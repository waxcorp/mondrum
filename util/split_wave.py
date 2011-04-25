#!/opt/local/bin/python2.6

import os
import sys
import wave

def split_wave(in_path, start=None, end=None):
  in_wave = wave.open(in_path)
  sampwidth = in_wave.getsampwidth()
  framerate = in_wave.getframerate()

  if start is None: start, end = 0, in_wave.getnframes()

  fname = os.path.splitext(in_path)[0] + '_%d_%d_%%s.wav' % (start, end)

  out_wave_l = wave.open(fname % 'l', 'w')
  out_wave_l.setnchannels(1)
  out_wave_l.setsampwidth(sampwidth)
  out_wave_l.setframerate(framerate)

  out_wave_r = wave.open(fname % 'r', 'w')
  out_wave_r.setnchannels(1)
  out_wave_r.setsampwidth(sampwidth)
  out_wave_r.setframerate(framerate)

  buflen = framerate * 16
  pos = start
  while pos < end:
    in_wave.setpos(pos)

    frame_data_l = frame_data_r = ''
    frame_data = in_wave.readframes(buflen)
    for x in xrange(len(frame_data) / (sampwidth * 2)):
      i = x * (sampwidth * 2)
      frame_data_l += frame_data[i:(i+sampwidth)]
      frame_data_r += frame_data[(i+sampwidth):(i+(sampwidth*2))]

    out_wave_l.writeframes(frame_data_l)
    out_wave_r.writeframes(frame_data_r)

    pos += buflen

  print 'complete:', out_wave_l._file.name
  print 'complete:', out_wave_r._file.name

  in_wave.close()
  out_wave_l.close()
  out_wave_r.close()

if __name__ == '__main__':
  in_path = sys.argv[1]

  start = end = None
  if sys.argv[1:]: start, end = int(sys.argv[2]), int(sys.argv[3])

  split_wave(in_path, start=start, end=end)
