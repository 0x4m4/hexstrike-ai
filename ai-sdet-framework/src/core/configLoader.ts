import * as fs from 'fs';
import * as path from 'path';

export interface AppConfig {
  appName: string;
  baseUrl: string;
  auth?: {
    username: string;
    password: string;
  };
  selectors: Record<string, Record<string, string>>;
}

export class ConfigLoader {
  static loadConfig(configName: string): AppConfig {
    const configPath = path.join(__dirname, `../../configs/${configName}.json`);
    if (!fs.existsSync(configPath)) {
      throw new Error(`Configuration file not found: ${configPath}`);
    }
    const rawData = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(rawData) as AppConfig;
  }
}
