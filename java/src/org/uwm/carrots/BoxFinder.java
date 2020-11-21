package org.uwm.carrots;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;

public class BoxFinder {

	private static int GAP_WIDTH = 20;
	
	private BufferedImage img;
	private Predicate<Color> cutoff;
	private List<ImageBox> foundImages = new ArrayList<>();
	private int minWidth;
	
	public BoxFinder(BufferedImage img, Predicate<Color> cutoff, int minWidth) {
		this.img = img;
		this.cutoff = cutoff;
		this.minWidth = minWidth;
	}
	
	private boolean isNewBox(int x, int y) {
		return !alreadyFound(x,y) && cutoff.test(new Color(img.getRGB(x, y)));
	}
	
	private static enum FoundBox {
		FOUND,
		PLUS_ONE,
		MINUS_ONE,
		NOT_FOUND
	}
	
	private FoundBox isBoxNearby(int x, int y, boolean modifyX) {
		if (alreadyFound(x,y)) {
			return FoundBox.NOT_FOUND;
		}
		
		if (!isNewBox(x,y)) {
			if ((modifyX && x < img.getWidth() - 1 && isNewBox(x + 1, y)) ||
					(!modifyX && y < img.getHeight() - 1 && isNewBox(x, y + 1))) {
				return FoundBox.PLUS_ONE;
			} else if ((modifyX && x > 0 && isNewBox(x - 1, y)) ||
					(!modifyX && y > 0 && isNewBox(x, y - 1))) {
				return FoundBox.MINUS_ONE;
			} else {
				return FoundBox.NOT_FOUND;
			}
		}
		return FoundBox.FOUND;
	}
		
	public List<ImageBox> findBoxes(boolean shortCircuit) {
		int x = 1;
		int y = 1;
		while (x < img.getWidth() - minWidth) {
			y = 1;
			while (y < img.getHeight() - minWidth) {
				// we've found our first corner. Now we need to find the bounding box.
				if (isNewBox(x,y)) {
					int upperLeftX = x;
					int upperLeftY = y;
					int maybeX = x;
					int maybeY = y;
					for (; maybeY < img.getHeight() - 1; maybeY++) {
						FoundBox found = isBoxNearby(maybeX, maybeY, true);
						if (found == FoundBox.PLUS_ONE) {
							maybeX++;
						} else if (found == FoundBox.MINUS_ONE) {
							maybeX--;
							upperLeftX--; // for this pass, we'll use a larger bounding box
						} else if (found == FoundBox.NOT_FOUND) {
							boolean jumpedGap = false;
							for (int i = 0; i < GAP_WIDTH && !jumpedGap && maybeY + i < img.getHeight() - 1; i++) {
								FoundBox foundGap = isBoxNearby(maybeX, maybeY + i, true);
								if (foundGap != FoundBox.NOT_FOUND) {
									jumpedGap = true;
								}
								if (found == FoundBox.PLUS_ONE) {
									maybeX++;
								} else if (found == FoundBox.MINUS_ONE) {
									maybeX--;
									upperLeftX--; // for this pass, we'll use a larger bounding box
								}
							}
							if (!jumpedGap) {
								break;
							}
						}
					}
					if (maybeY - y > minWidth) {
						int lowerRightY = maybeY;
						
						maybeX = x;
						maybeY = y;
						for (; maybeX < img.getWidth() - 1; maybeX++) {
							FoundBox found = isBoxNearby(maybeX, maybeY, false);
							if (found == FoundBox.PLUS_ONE) {
								maybeY++;
							} else if (found == FoundBox.MINUS_ONE) {
								maybeY--;
								upperLeftY--; // for this pass, we'll use a larger bounding box
							} else if (found == FoundBox.NOT_FOUND) {
								boolean jumpedGap = false;
								for (int i = 0; i < GAP_WIDTH && !jumpedGap && maybeX + i < img.getWidth() - 1; i++) {
									FoundBox foundGap = isBoxNearby(maybeX + i, maybeY, false);
									if (foundGap != FoundBox.NOT_FOUND) {
										jumpedGap = true;
									}
									if (found == FoundBox.PLUS_ONE) {
										maybeY++;
									} else if (found == FoundBox.MINUS_ONE) {
										maybeY--;
										upperLeftY--; // for this pass, we'll use a larger bounding box
									}

								}
								if (!jumpedGap) {
									break;
								}
							}
						}
						if (maybeX - x > minWidth) {
							upperLeftY = Math.max(0, upperLeftY);
							upperLeftX = Math.max(0, upperLeftX);
							maybeX = Math.min(img.getWidth(), maybeX);
							lowerRightY = Math.min(img.getHeight(), lowerRightY);
							if (verifySides(upperLeftX, upperLeftY, maybeX, lowerRightY)) {
								//System.out.println("Edge of box from: (" + x + ", " + y + ") to (" + maybeX + ", " + lowerRightY + ")");
								foundImages.add(new ImageBox(upperLeftX, upperLeftY, maybeX, lowerRightY, img));
								if (shortCircuit) {
									return foundImages;
								}
							}
						}
					}
				}
				y++;
			}
			x++;
		}
		return foundImages;
	}

	private boolean verifySides(int ulX, int ulY, int lrX, int lrY) {
		int nMatched = 0; // count the number of rows that match the supposedly-right edge
		for (int y = ulY; y < lrY; y++) {
			for (int x = lrX - 1; x > lrX - 50 && x > 0; x--) {
				FoundBox found = isBoxNearby(x, y, true);
				if (found != FoundBox.NOT_FOUND) {
					nMatched++;
					break;
				}
			}
		}
		if (nMatched > (lrY - ulY)*.8) {
			return true;
		}
//		System.out.println("Rejecting box");
		return false;
	}

	private boolean alreadyFound(int x, int y) {
		for (ImageBox box : foundImages) {
			if (box.contains(x, y)) {
				return true;
			}
		}
		return false;
	}
}
