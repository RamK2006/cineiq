export function srtToVtt(srtContent: string): string {
  let vtt = 'WEBVTT\n\n';
  const lines = srtContent.replace(/\r\n/g, '\n').split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Convert time line in SRT: 00:00:01,000 --> 00:00:04,000 to VTT: 00:00:01.000 --> 00:00:04.000
    if (line.includes('-->')) {
      vtt += line.replace(/,/g, '.') + '\n';
    } 
    // Skip numeric cue identifiers just before the time line
    else if (/^\d+$/.test(line.trim()) && lines[i + 1] && lines[i + 1].includes('-->')) {
      continue;
    }
    else {
      vtt += line + '\n';
    }
  }
  
  return vtt;
}

export async function fetchAndProcessSubtitle(url: string, format: 'vtt' | 'srt'): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load subtitle from ${url}: ${response.statusText}`);
  }
  
  const content = await response.text();
  
  if (format === 'srt') {
    const vttContent = srtToVtt(content);
    const blob = new Blob([vttContent], { type: 'text/vtt' });
    return URL.createObjectURL(blob);
  } else {
    // If it's already VTT, just create an object URL to normalize it, 
    // or return the URL directly if CORS is not an issue. 
    // Creating object URL avoids CORS issues with tracks on canvas if we ever need it.
    const blob = new Blob([content], { type: 'text/vtt' });
    return URL.createObjectURL(blob);
  }
}
