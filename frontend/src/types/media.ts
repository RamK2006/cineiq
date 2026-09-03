export type SubtitleFormat = 'vtt' | 'srt';
export type SubtitleKind = 'subtitles' | 'captions' | 'descriptions' | 'chapters' | 'metadata';

export interface SubtitleTrackData {
  id: string;
  label: string;
  language: string;
  src: string;
  kind?: SubtitleKind;
  format?: SubtitleFormat;
  default?: boolean;
}

export type SubtitleFontSize = 'small' | 'medium' | 'large';
export type SubtitleBackgroundOpacity = 'low' | 'medium' | 'high';

export interface SubtitlePreferences {
  fontSize: SubtitleFontSize;
  backgroundOpacity: SubtitleBackgroundOpacity;
}

export interface MediaSource {
  id: string;
  title: string;
  url: string;
  type?: string;
}
