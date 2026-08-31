export interface SubtitleTrackData {
  id: string;
  language: string;
  label: string;
  src?: string;
  kind?: string;
  format?: string;
}


export interface MediaSource {
  id: string;
  title: string;
  url: string;
  type?: string;
}
