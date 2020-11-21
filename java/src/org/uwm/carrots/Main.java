package org.uwm.carrots;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

import javax.imageio.ImageIO;

import com.google.zxing.BinaryBitmap;
import com.google.zxing.LuminanceSource;
import com.google.zxing.MultiFormatReader;
import com.google.zxing.NotFoundException;
import com.google.zxing.Result;
import com.google.zxing.client.j2se.BufferedImageLuminanceSource;
import com.google.zxing.common.HybridBinarizer;

public class Main {
	
	private static File outputDir = new File(".");

	public static void main(String[] args) throws Exception {
		File file = new File(args[0]);
		if (args.length != 3 && args.length != 4) {
			throw new IllegalArgumentException("Expected <file input> <output root dir> <expected num carrots> <inverted (optional)>");
		}
		outputDir = new File(args[1]);
		int numCarrots = Integer.parseInt(args[2]);
		boolean invert = args.length == 4 && args[3].equalsIgnoreCase("inverted");
		if (args.length == 4 && !invert) {
			throw new IllegalArgumentException("Unrecognized final option: expected <file input> <output root dir> <expected num carrots> <inverted (optional)>");
		}
		process(file, numCarrots, invert);
	}
	
	private static final Predicate<Color> CARROT_DETECT = color -> (color.getRed() > 50 && color.getBlue() < 50) ||
			color.getRed() - color.getBlue() > 30;
	
	private static void process(File f, int numCarrots, boolean invert) throws Exception {
		// step 1: extract the black rectangles into their own files
		BufferedImage img = ImageIO.read(f);
		Predicate<Color> adjustedBlackWhiteCutoff = findAdjustedCutoff(img, invert);
		List<ImageBox> results = new BoxFinder(img, adjustedBlackWhiteCutoff, 600).findBoxes(false);
		System.out.println("Processing file " + f.getName() + ", found " + results.size() + " sub-images");
		Map<File, BufferedImage> toWrite = new HashMap<File, BufferedImage>();
		for (int i = 0; i < results.size(); i++) {
			BufferedImage crop = results.get(i).crop();
			// Scale is detected outside this pipeline
			//int ppm = ScaleFinder.findPixelsPerMeter(crop);
			boolean carrotFound = !(new BoxFinder(crop, CARROT_DETECT, 30).findBoxes(true).isEmpty());
			// now grab the qr code; null means none found
			String fileName = extract(crop);

			// write the output
			File output;
			File folder;
			if (fileName != null && carrotFound) {
				int sourceStart = fileName.indexOf("Source_") + "Source_".length();
				folder = new File(outputDir, fileName.substring(sourceStart, fileName.indexOf("}", sourceStart)));

				if (!folder.exists()) {
					folder.mkdirs();
				}

				fileName = fileName.substring(fileName.indexOf("{"), fileName.lastIndexOf("}") + 1);
				
				// scale is detected outside this pipeline
				//fileName += "{Scale_" + ppm + "_ppm}";
				output = new File(folder, fileName + "{Photo_0}" + ".png");

				int numCopies = 1;
				while (output.exists()) {
					output = new File(folder, fileName + "{Photo_" + numCopies + "}" + ".png");
					numCopies++;
				}
				toWrite.put(output,  crop);
			}
		}
		if (toWrite.size() != numCarrots) {
			throw new IllegalArgumentException("Expected " + numCarrots + " carrots with QR codes, but found " + toWrite.size());
		}
		toWrite.forEach((output, crop) -> {
			try {
				ImageIO.write(crop, "png", output);
			} catch (IOException e) {
				throw new RuntimeException(e);
			}
		});
	}

	private static Predicate<Color> findAdjustedCutoff(BufferedImage img, boolean invert) {
		long min = 0;
		int nMin = 0;
		long max = 0;
		int nMax = 0;
		for (int x = 0; x < img.getWidth(); x++) {
			for (int y = 0; y < img.getHeight(); y++) {
				Color c = new Color(img.getRGB(x,  y));
				if (c.getRed() - c.getBlue() < 15) {
					if (c.getRed() < 60) {
						min += c.getRed();
						nMin++;
					} else if (c.getRed() > 110) {
						max += c.getRed();
						nMax++;
					}
				}
				
			}
		}
		if (nMin == 0) {
			nMin++;
		}
		if (nMax == 0) {
			nMax++;
		}
		min /= nMin;
		max /= nMax;
		int avg = (int) ((min + max)/2);

		return invert ? color -> color.getRed() > avg : color -> color.getRed() < avg;
	}

	private static String extract(BufferedImage bufferedImage) throws Exception {
        LuminanceSource source = new BufferedImageLuminanceSource(bufferedImage);
        BinaryBitmap bitmap = new BinaryBitmap(new HybridBinarizer(source));

        try {
            Result result = new MultiFormatReader().decode(bitmap);
            return result.getText();
        } catch (NotFoundException e) {
            return null;
        }
	}

}
