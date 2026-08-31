import { srtToVtt, fetchAndProcessSubtitle } from '../../utils/subtitles';

describe('Subtitle Utils', () => {
  describe('srtToVtt', () => {
    it('converts basic SRT to VTT correctly', () => {
      const srt = `1\n00:00:01,000 --> 00:00:04,000\nHello world\n\n2\n00:00:05,000 --> 00:00:09,000\nLine 2`;
      const vtt = srtToVtt(srt);
      
      expect(vtt).toContain('WEBVTT\n\n');
      expect(vtt).toContain('00:00:01.000 --> 00:00:04.000');
      expect(vtt).toContain('Hello world');
      expect(vtt).toContain('00:00:05.000 --> 00:00:09.000');
      expect(vtt).toContain('Line 2');
      
      // Should omit numeric cue identifiers if possible, or at least preserve correct time formats
      expect(vtt).not.toContain('\n1\n');
      expect(vtt).not.toContain('\n2\n');
    });

    it('handles CRLF line endings', () => {
      const srt = `1\r\n00:00:01,000 --> 00:00:04,000\r\nHello\r\n\r\n2\r\n00:00:05,000 --> 00:00:09,000\r\nWorld`;
      const vtt = srtToVtt(srt);
      expect(vtt).toContain('00:00:01.000 --> 00:00:04.000\nHello');
    });
    
    it('preserves multiline cues', () => {
      const srt = `1\n00:00:01,000 --> 00:00:04,000\nHello\nWorld\n\n`;
      const vtt = srtToVtt(srt);
      expect(vtt).toContain('Hello\nWorld');
    });
  });

  describe('fetchAndProcessSubtitle', () => {
    const originalFetch = global.fetch;
    const originalCreateObjectURL = URL.createObjectURL;

    beforeEach(() => {
      global.fetch = jest.fn();
      URL.createObjectURL = jest.fn(() => 'blob:dummy-url');
    });

    afterEach(() => {
      global.fetch = originalFetch;
      URL.createObjectURL = originalCreateObjectURL;
    });

    it('fetches and converts SRT format to VTT Blob URL', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        text: async () => '1\n00:00:01,000 --> 00:00:04,000\nTest'
      });

      const url = await fetchAndProcessSubtitle('/test.srt', 'srt');
      expect(url).toBe('blob:dummy-url');
      expect(global.fetch).toHaveBeenCalledWith('/test.srt');
      expect(URL.createObjectURL).toHaveBeenCalled();
    });

    it('fetches VTT format directly to Blob URL', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        text: async () => 'WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nTest'
      });

      const url = await fetchAndProcessSubtitle('/test.vtt', 'vtt');
      expect(url).toBe('blob:dummy-url');
      expect(global.fetch).toHaveBeenCalledWith('/test.vtt');
      expect(URL.createObjectURL).toHaveBeenCalled();
    });

    it('throws error when fetch fails', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found'
      });

      await expect(fetchAndProcessSubtitle('/missing.vtt', 'vtt')).rejects.toThrow('Failed to load subtitle');
    });
  });
});
