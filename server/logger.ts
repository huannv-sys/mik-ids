/**
 * Logger module for application
 */

// Simple logger implementation
class Logger {
  public info(message: string, ...args: any[]) {
    console.log(`[INFO] ${message}`, ...args);
  }

  public warn(message: string, ...args: any[]) {
    console.warn(`[WARN] ${message}`, ...args);
  }

  public error(message: string, ...args: any[]) {
    console.error(`[ERROR] ${message}`, ...args);
  }

  public debug(message: string, ...args: any[]) {
    if (process.env.DEBUG === 'true') {
      console.debug(`[DEBUG] ${message}`, ...args);
    }
  }
}

export const logger = new Logger();