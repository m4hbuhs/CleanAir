export interface Station {
  id: string;
  name: string;
  lat: number;
  lon: number;
  current_pm25: number;
  forecast_24h: number[];
}

export interface Incident {
  id: string;
  type: string;
  lat: number;
  lon: number;
  trust_score: number;
  exif_match: boolean;
  telemetry_match: boolean;
  explanation: string;
  command: string;
  expected_reduction: string;
  resources: { type: string; quantity: number | string }[];
  timestamp: string;
}
