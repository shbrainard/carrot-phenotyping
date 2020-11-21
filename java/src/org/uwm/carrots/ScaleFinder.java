package org.uwm.carrots;

import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;

import javax.imageio.ImageIO;

public class ScaleFinder {
	public static void main(String[] args) throws Exception {
		File file = new File(args[0]);
		if (args.length != 1) {
			throw new IllegalArgumentException("Expected <file or directory input>, renames files with pixels-per-meter post-pended");
		}
		bulkProcess(file);
	}
	
	private static void bulkProcess(File f) throws Exception {
		if (f.isDirectory()) {
			for (File file : f.listFiles()) {
				bulkProcess(file);
			}
		} else {
			BufferedImage img = ImageIO.read(f);
			if (img != null) {
				int nPixels = findPixelsPerMeter(img);
				if (nPixels < 0) {
					System.err.println("Unable to find scale for file " + f.getName());
				} else {
					String suffix = f.getName().substring(f.getName().lastIndexOf(".") + 1);
					String prefix = f.getName().substring(0, f.getName().lastIndexOf("."));
					if (prefix.toLowerCase().contains("{scale_")) {
						int index = prefix.toLowerCase().indexOf("{scale_");
						prefix = prefix.substring(0, index) + prefix.substring(prefix.indexOf("}", index) + 1);
					}
					File dest = new File(f.getParentFile(), prefix +"{Scale_"+nPixels+"_ppm}."  + suffix);
					if (!f.renameTo(dest)) {
						System.err.println("Unable to rename file " + f.getName() + " to " + dest.getName());
					}
				}
			}
		}
	}

	public static int findPixelsPerMeter(BufferedImage img) {
		int nPixels = findGreenScale(img);
		
		// green line is 10cm, so x10 to get pixels-per-meter
		nPixels *= 10;
		
		if (nPixels < 0) {
			nPixels = findBlueCircle(img);
			// blue circle is 37 mm, so x27 to get pixels-per-meter
			nPixels *= 27;
		}
		return nPixels;
	}

	private static int findBlueCircle(BufferedImage img) {
		// look for vertical segments to avoid picking up the lollipop part of the circle
		int maxBlueLine = -1;
		for (int x = 0; x < img.getWidth(); x++) {
			for (int y = 0; y < img.getHeight(); y++) {
				if (isBlue(img, x, y)) {
					int lineLen = findVerticalLine(x, y, img);
					maxBlueLine = Math.max(maxBlueLine, lineLen);
				}
			}
		}
		return maxBlueLine;
	}

	private static boolean isBlue(BufferedImage img, int x, int y) {
		Color c = new Color(img.getRGB(x,  y));
		return c.getGreen() - c.getRed() > 20 && c.getBlue() - c.getGreen() > 15;
	}

	private static int findGreenScale(BufferedImage img) {
		int maxGreenLine = -1;
		for (int x = 0; x < img.getWidth(); x++) {
			for (int y = 0; y < img.getHeight(); y++) {
				if (isGreen(img, x, y)) {
					int lineLen = findLine(x, y, img);
					if (lineLen > 50) { // avoid spurious results from the carrot top
						maxGreenLine = Math.max(maxGreenLine, lineLen);
					}
				}
			}
		}
		return maxGreenLine;
	}
	
	private static int findVerticalLine(int x, int y, BufferedImage img) {
		int count = 0;
		for (int yInc = y; yInc < img.getHeight(); yInc++) {
			if (isBlue(img, x, yInc)) {
				count++;
			} else {
				break;
			}
		}
		return count;
	}

	private static int findLine(int x, int y, BufferedImage img) {
		int count = 0;
		for (int xInc = x; xInc < img.getWidth(); xInc++) {
			if (isGreen(img, xInc, y)) {
				count++;
			} else {
				break;
			}
		}
		return count;
	}

	private static boolean isGreen(BufferedImage img, int x, int y) {
		Color c = new Color(img.getRGB(x,  y));
		return c.getGreen() > 220 && c.getBlue() < 150 && c.getRed() < 150;
	}
}
