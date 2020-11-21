package org.uwm.carrots;
import java.util.HashMap;
import java.util.Map;

public class Timer {

	public static enum TimeType {
		OUTER_BOXES,
		QR_CODES,
		WRITE
	}
	
	private Map<TimeType, Long> times = new HashMap<>();
	
	private long currPhaseStart = System.currentTimeMillis();
	private int totalPhases = 0;
	private int whenToPrint;
	
	public Timer(int whenToPrint) {
		for (TimeType type : TimeType.values()) {
			times.put(type, 0L);
		}
		this.whenToPrint = whenToPrint;
	}

	public synchronized void endPhase(TimeType type) {
		totalPhases++;
		times.put(type, times.get(type) + System.currentTimeMillis() - currPhaseStart);
		currPhaseStart = System.currentTimeMillis();
		if (whenToPrint > 0 && totalPhases % whenToPrint == 0) {
			printStatsSoFar();
		}
	}
	
	private void printStatsSoFar() {
		times.forEach((type, total) -> System.out.println("Phase " + type + " took " + total/1000 + " seconds so far"));
	}
}
