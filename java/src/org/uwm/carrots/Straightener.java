package org.uwm.carrots;

import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

public class Straightener {
	
	private static final int BLACK = Color.BLACK.getRGB();
	private static final int WHITE = Color.WHITE.getRGB();
	
	public static void main(String[] args) throws Exception {
		File file = new File(args[0]);
		if (args.length != 1) {
			throw new IllegalArgumentException("Expected <file or directory input>, outputs a side-by-side file with <amount of curvature>px post-pended");
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
				// new width calculation de-blobs without preprocessing
				//img = preprocess(img);
				Pair<Integer, List<List<Integer>>> resultPair = process(img);
				List<List<Integer>> result = resultPair.rhSide;
				BufferedImage toWrite = new BufferedImage(result.size(), result.get(0).size(), img.getType());
				for (int x = 0; x < result.size(); x++) {
					for (int y = 0; y < result.get(0).size(); y++) {
						toWrite.setRGB(-1*(x - result.size() + 1), y, result.get(x).get(y));
					}
				}
				String suffix = f.getName().substring(f.getName().lastIndexOf(".") + 1);
				
				int pixelAdjust = resultPair.lhSide;
				if (f.getName().toLowerCase().contains("{scale_")) {
					int start = f.getName().toLowerCase().indexOf("{scale_") + 7;
					int end = f.getName().indexOf("}", start + 1);
					int ppm;
					try {
						ppm = Integer.parseInt(f.getName().substring(start, end));
					} catch (NumberFormatException e) { // probably scale is in medium format, which was also per mm
						ppm = 100*Integer.parseInt(f.getName().substring(start, f.getName().indexOf("_", start + 1)));
					}
					
					// the scale in the filename is actually pixels per 10 cm, this converts to pixel per mm without angering the gods of int division
					pixelAdjust *=100; 
					pixelAdjust /= ppm;
				}
				
				ImageIO.write(toWrite, suffix, 
						new File(f.getParentFile(), f.getName().substring(0, f.getName().lastIndexOf("."))+"{Curvature_" + pixelAdjust + "}."  + suffix));
			}
		}
	}
	
	private static BufferedImage preprocess(BufferedImage img) {
		Pair<Integer, Integer> prevSize = null;
		int expansionX = -1;
		int expansionY = -1;
		int minWidth = img.getHeight();
		
		for (int x = img.getWidth()/4; x > 0; x--) {
			Pair<Integer, Integer> carrot = findCarrot(img, x);
			
			if (carrot.lhSide >= 0) {
				if (prevSize != null) {
					// the carrot has bent too far if it is "expanding" rapidly along its length
					if (carrot.rhSide - carrot.lhSide > 1.5*minWidth) {
						expansionX = x;
						expansionY = (prevSize.rhSide + prevSize.lhSide) / 2;
						break;
					}
				}
				minWidth = Math.min(minWidth, carrot.rhSide - carrot.lhSide);
				prevSize = carrot;
			}
			
		}
		
		if (expansionX > 0) {
			int deltaX = Math.max(0, expansionY - expansionX);
			int deltaY = Math.max(0, expansionX - expansionY);
			BufferedImage result = new BufferedImage(img.getWidth() + deltaX, img.getHeight() + deltaY, img.getType());
			// copy everything that isn't getting reflected
			for (int x = img.getWidth() - 1; x > expansionX; x--) {
				for (int y = 0; y < img.getHeight(); y++) {
					result.setRGB(x + deltaX, y + deltaY, img.getRGB(x, y));
				}
			}
			for (int x = 0; x <= expansionX; x++) {
				for (int y = expansionY + 1; y < img.getHeight(); y++) {
					result.setRGB(x + deltaX, y + deltaY, img.getRGB(x, y));
				}
			}
			
			// reflect along the diagonal to the point of curving. Open question: does this mess up curvature calculations
			for (int x = 0; x <= expansionX; x++) {
				for (int y = 0; y <= expansionY; y++) {
					result.setRGB(y + deltaY, x + deltaX, img.getRGB(x, y));
				}
			}
			return result;
		} else {
			return img;
		}
	}
	
	private static class ColData {
		int x;
		int centerY;
		int nominalWidth;
		int relAdjust;
		
		public ColData(int x, int centerY, int nominalWidth, int relAdjust) {
			this.x = x;
			this.centerY = centerY;
			this.nominalWidth = nominalWidth;
			this.relAdjust = relAdjust;
		}
	}
	
	private static final int WINDOW_SIZE = 12;
	
	private static List<ColData> getColumnData(BufferedImage bitmap) {
		List<ColData> result = new ArrayList<>();
		int centerline = bitmap.getHeight() / 2;
		boolean firstColAdjusted = false;
		int prevColAdjusted = 0;
		
		for (int x = bitmap.getWidth() - 1; x >= 0; x--) {
			Pair<Integer, Integer> carrot = findCarrot(bitmap, x);
			if (carrot.lhSide < 0) { // no carrot, trim
				continue;
			}
			
			int adjustCol = 0;
			int width = carrot.rhSide - carrot.lhSide;
			// adjust to the center
			int currCenter = (carrot.rhSide - carrot.lhSide) / 2 + carrot.lhSide;
			adjustCol = centerline - currCenter;			
			
			result.add(new ColData(x, currCenter, width, firstColAdjusted ? prevColAdjusted - adjustCol : 0));
			firstColAdjusted = true;
			prevColAdjusted = adjustCol;
		}
		return result;
	}

	private static Pair<Integer, List<List<Integer>>> process(BufferedImage bitmap) {
		List<List<Integer>> result = new ArrayList<>();
		int centerline = bitmap.getHeight() / 2;
		double adjustRow = 0;
		
		int totalAdjustment = 0;
		
		List<ColData> columns = getColumnData(bitmap);
		Pair<Integer, Integer> firstCenter = new Pair<>(columns.get(0).x, columns.get(0).centerY);
		Pair<Integer, Integer> lastCenter = new Pair<>(columns.get(columns.size() - 1).x, columns.get(columns.size() - 1).centerY);
		
		for (int i = 1; i < columns.size(); i++) {
			int adj1 = columns.get(i - 1).relAdjust;
			int adj2 = columns.get(i).relAdjust;
			if (Math.abs(adj1 + adj2) < Math.abs(adj1) + Math.abs(adj2)) { // one is positive, one is negative
				int delta = Math.min(Math.abs(adj1), Math.abs(adj2));
				if (columns.get(i - 1).relAdjust < 0) {
					columns.get(i - 1).relAdjust += delta;
					columns.get(i).relAdjust -= delta;
				} else {
					columns.get(i - 1).relAdjust -= delta;
					columns.get(i).relAdjust += delta;
				}
			}
		}
		for (int i = 1; i < columns.size() - 1; i++) {
			int adj1 = columns.get(i - 1).relAdjust;
			int adj2 = columns.get(i + 1).relAdjust;
			if (Math.abs(adj1 + adj2) < Math.abs(adj1) + Math.abs(adj2)) { // one is positive, one is negative
				int delta = Math.min(Math.abs(adj1), Math.abs(adj2));
				if (columns.get(i - 1).relAdjust < 0) {
					columns.get(i - 1).relAdjust += delta;
					columns.get(i + 1).relAdjust -= delta;
				} else {
					columns.get(i - 1).relAdjust -= delta;
					columns.get(i + 1).relAdjust += delta;
				}
			}
		}
		
		List<Integer> unsmoothedWidth = new ArrayList<>();
		for (int colIndex = 0; colIndex < columns.size(); colIndex++) {
			ColData col = columns.get(colIndex);
			int width = col.nominalWidth;

			// the width is actually the cross section perpendicular to the midline, which is only a vertical cross section for a carrot already lying parallel
			// to the x axis. We smooth the slope over a window of 3 pixels
			double currentSlope = findSlope(columns, colIndex);
						
			if (currentSlope != 0) {
				double perpendicularSlope = -1*(1.0 / currentSlope);
				width = Math.max(1, findWidth(bitmap, perpendicularSlope, col.x, col.centerY));
			}
			unsmoothedWidth.add(width);
		}
		
		for (int colIndex = 0; colIndex < columns.size(); colIndex++) {
			ColData col = columns.get(colIndex);
			int width = smoothWidth(unsmoothedWidth, colIndex);
			// adjust to the center
			int currCenter = col.centerY;

			// in general, we prefer to treat modest S curves as "straighter" than a C curve,
			// so don't take the absolute value
			totalAdjustment += currCenter - firstCenter.rhSide;

			// the width is actually the cross section perpendicular to the midline, which is only a vertical cross section for a carrot already lying parallel
			// to the x axis. We smooth the slope over a window of 3 pixels
			double currentSlope = findSlope(columns, colIndex);
			
			// track how much we're changing the length: if we're moving columns relative to their neighbors,
			// calculate the difference
			adjustRow += Math.sqrt(currentSlope * currentSlope + 1) - 1.0;

			// trim any root hairs, and record the appropriate centered width
			int carrotStart = centerline - width/2;
			List<Integer> adjusted = new ArrayList<>();
			for (int i = 0; i < carrotStart; i++) {
				adjusted.add(BLACK);
			}
			for (int i = 0; i < width && adjusted.size() < bitmap.getHeight(); i++) {
				adjusted.add(WHITE);
			}
			while (adjusted.size() < bitmap.getHeight()) {
				adjusted.add(BLACK);
			}
			
			result.add(adjusted);
			
			// account for length changes
			if (adjustRow > .5) {
				result.add(adjusted);
				adjustRow -= 1;
			}
		}
		cropToCarrot(result);
		
		// figure out how much adjustment would happen because of the diagonal angle, subtract that out
		int integralOfDiagonal = Math.abs((lastCenter.lhSide - firstCenter.lhSide - 1)*(firstCenter.rhSide - lastCenter.rhSide) / 2);
		
		return new Pair<>((int)(Math.sqrt(Math.abs(totalAdjustment - integralOfDiagonal))), result);
	}

	private static void cropToCarrot(List<List<Integer>> result) {
		int yMax = 0, yMin = Integer.MAX_VALUE;
		int height = result.get(0).size();
		for (List<Integer> col : result) {
			for (int i = 0; i < col.size(); i++) {
				if (col.get(i) == WHITE) {
					yMax = Math.max(i, yMax);
					yMin = Math.min(i, yMin);
				}
			}
		}
		
		for (List<Integer> col : result) {
			if (col.size() != height) {
				continue; // duped row has already been trimmed
			}
			for (int i = 0; i <yMin; i++) {
				col.remove(0);
			}
			for (int i = 0; i < height - yMax - 1; i++) {
				col.remove(col.size() - 1);
			}
		}
		
	}

	private static int SMOOTHING_WINDOW = 20;
	private static int smoothWidth(List<Integer> unsmoothedWidths, int index) {
		int sum = 0;
		int num = 0;
		for (int i = Math.max(index - SMOOTHING_WINDOW / 2, 0); i < Math.min(index + SMOOTHING_WINDOW / 2, unsmoothedWidths.size()); i++) {
			sum += unsmoothedWidths.get(i);
			num++;
		}
		
		return sum / num;
	}

	private static int findWidth(BufferedImage bitmap, double slope, final int x, final int y) {
		int xRight = x;
		double yRight = y;
		while (inBounds(bitmap, xRight, (int)yRight) && isCarrot(bitmap, xRight, (int)yRight)) {
			xRight++;
			yRight += slope;
		}
		// rounding
		if (!inBounds(bitmap, xRight, (int)(yRight - slope/2)) || !isCarrot(bitmap, xRight, (int)(yRight - slope/2))) {
			xRight--;
			yRight -=slope;
		}
		
		int xLeft = x;
		double yLeft = y;
		while (inBounds(bitmap, xLeft, (int)yLeft) && isCarrot(bitmap, xLeft, (int)yLeft)) {
			xLeft--;
			yLeft -= slope;
		}
		// rounding
		if (!inBounds(bitmap, xLeft, (int)(yLeft + slope/2)) || !isCarrot(bitmap, xLeft, (int)(yLeft + slope/2))) {
			xLeft++;
			yLeft +=slope;
		}
		
		return (int)Math.sqrt((xRight - xLeft)*(xRight - xLeft) + (yRight - yLeft)*(yRight - yLeft));
	}

	private static boolean inBounds(BufferedImage bitmap, int x, int y) {
		return x >= 0 && y >= 0 && x < bitmap.getWidth() && y < bitmap.getHeight();
	}

	private static double findSlope(List<ColData> columns, int index) {
		int sum = 0;
		int num = 0;
		for (int i = Math.max(index - WINDOW_SIZE / 2, 0); i < Math.min(index + WINDOW_SIZE / 2, columns.size()); i++) {
			sum += columns.get(i).relAdjust;
			num++;
		}
		
		//weight the closer values more
		for (int i = Math.max(index - WINDOW_SIZE / 4, 0); i < Math.min(index + WINDOW_SIZE / 4, columns.size()); i++) {
			sum += columns.get(i).relAdjust;
			num++;
		}
		return sum == 0 ? 0 : sum / (-1.0*num);
	}


	private static final int THRESHOLD = 100; // root hairs are less than 50 pixels
	
	private static Pair<Integer, Integer> findCarrot(BufferedImage img, int x) {
		int start = -1, end = img.getHeight() - 1;
		int curStart = -1, curEnd = img.getHeight() - 1;
		for (int y = 0; y < img.getHeight(); y++) {
			if (isCarrot(img, x, y) && curStart < 0) {
				curStart = y;
			}
			if (!isCarrot(img, x, y) && curStart >=0) {
				curEnd = y - 1;
				
				// if the current segment is a better carrot candidate, and the previous segment is unset or small enough to be a root hair, 
				// switch to the current segment
				if (start < 0 || ((end - start) < (curEnd - curStart) && (end - start) < THRESHOLD)) {
					start = curStart;
					end = curEnd;
				} else if (curEnd - curStart >= THRESHOLD && end - start >= THRESHOLD) {
					// if the previous segment and the current segment are both too big to be root hairs, 
					// combine them, we probably have a weird spec on the carrot
					end = curEnd;
				}
				
				// now reset our current segment
				curStart = -1;
				curEnd = img.getHeight() - 1;
			}
		}
		
		// handle segments that continue to the edge of the image
		if (curStart >=0) {
			// if the current segment is a better carrot candidate, and the previous segment is unset or small enough to be a root hair, 
			// switch to the current segment
			if (start < 0 || ((end - start) < (curEnd - curStart) && (end - start) < THRESHOLD)) {
				start = curStart;
				end = curEnd;
			} else if (curEnd - curStart >= THRESHOLD && end - start >= THRESHOLD) {
				// if the previous segment and the current segment are both too big to be root hairs, 
				// combine them, we probably have a weird spec on the carrot
				end = curEnd;
			}
		}
		return new Pair<Integer, Integer>(start, end);
	}
	
	private static boolean isCarrot(BufferedImage img, int x, int y) {
		return new Color(img.getRGB(x, y)).getRed() > 128;
	}
	
	public static class Pair<K, V> {
		private final K lhSide;
		private final V rhSide;
		
		public Pair(K lhSide, V rhSide) {
			this.lhSide = lhSide;
			this.rhSide = rhSide;
		}

		@Override
		public String toString() {
			return "(" + lhSide + ", " + rhSide + ")";
		}
	}
}
