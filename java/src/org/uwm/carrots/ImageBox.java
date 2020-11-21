package org.uwm.carrots;
import java.awt.image.BufferedImage;

public class ImageBox {
	private int upperLeftX;
	private int upperLeftY;
	private int lowerRightX;
	private int lowerRightY;
	private BufferedImage orig;

	public ImageBox(int upperLeftX, int upperLeftY, int lowerRightX, int lowerRightY, BufferedImage orig) {
		this.upperLeftX = Math.max(0, upperLeftX);
		this.upperLeftY = Math.max(0, upperLeftY);
		this.lowerRightX = Math.min(orig.getWidth(), lowerRightX);
		this.lowerRightY = Math.min(orig.getHeight(), lowerRightY);
		this.orig = orig;
	}

	public boolean contains(int x, int y) {
		return x <= lowerRightX && x >= upperLeftX && y <= lowerRightY && y >= upperLeftY;
	}
	
	public BufferedImage crop() {
		return orig.getSubimage(upperLeftX, upperLeftY, lowerRightX - upperLeftX, lowerRightY - upperLeftY);
	}
}
