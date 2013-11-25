from collections import defaultdict
import cPickle
import glob
import numpy
import os
import sys
import yaafelib



# online PCA for large datasets
class PCA:
  def start(self, ndim):
    self.ndim = ndim
    self.mean = numpy.zeros(self.ndim, dtype='float64')
    self.covariance = numpy.zeros((self.ndim,)*2, dtype='float64')
    self.num_frames = 0

  def add(self, x):
    #if not hasattr(self, 'ndim') or self.ndim != x.shape[1]:
    if not hasattr(self, 'ndim'):
      self.start(x.shape[1])

    mean = x.mean(axis=0)
    centered = x - mean
    covariance = numpy.dot(centered.T, centered)
    difference = mean - self.mean
    self.covariance += covariance + numpy.outer(difference, difference) * len(x) * self.num_frames / float(len(x) + self.num_frames)
    self.mean += difference * len(x) / float(len(x) + self.num_frames)
    self.num_frames += len(x)

  def pca(self, keep_variance=1.0, add_variance=1e-7, diagonal=False):
    covariance = 0.5 * (self.covariance + self.covariance.T) / (self.num_frames - 1)
    if diagonal:
      covariance = numpy.diag(numpy.diag(covariance))
    values, vectors = numpy.linalg.eigh(covariance)
    indices = values.argsort()[::-1]
    values = values[indices]
    cutoff = (values.cumsum() / values.sum()).searchsorted(keep_variance, side='right')
    print 'kept %i/%i (%.2f%%) dimensions' % (cutoff, len(values), 100.0*cutoff/len(values))
    values = values[:cutoff]
    vectors = vectors[:, indices[:cutoff]]
    self.transform = vectors / numpy.sqrt(values + add_variance)

  def feature(self, x):
    return numpy.dot(x-self.mean, self.transform)


def file_create(name):
  directory = os.path.dirname(name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  return file(name, 'w')

pca = None

def export_features(path=None, audiofiles=None, out='../audio_features', train_file_path=None):
  # prepare the FeaturePlan
  plan = yaafelib.FeaturePlan(sample_rate=48000, normalize=0.99)
  size_info = 'blockSize=1248 stepSize=624'
  if pca is None:
      global pca

  features = [
    'ZCR',
    'TemporalShapeStatistics',
    'Energy',
    'MagnitudeSpectrum',
    'SpectralVariation',
    'SpectralSlope',
    'SpectralRolloff',
    'SpectralShapeStatistics',
    'SpectralFlux',
    'SpectralFlatness',
    'SpectralDecrease',
    'SpectralFlatnessPerBand',
    'SpectralCrestFactorPerBand',
    'AutoCorrelation',
    'LPC',
    'LSF',
    'ComplexDomainOnsetDetection',
    'MelSpectrum',
    'MFCC: MFCC CepsNbCoeffs=22',
    'MFCC_d1: MFCC %s > Derivate DOrder=1',
    'MFCC_d2: MFCC %s > Derivate DOrder=2',
    'Envelope',
    'EnvelopeShapeStatistics',
    'AmplitudeModulation',
    'Loudness',
    'PerceptualSharpness',
    'PerceptualSpread',
    'OBSI',
    'OBSIR']

  for f in features:
    if ':' not in f: f = '%s: %s' % (f, f)
    if '%s' not in f: f += ' %s'
    plan.addFeature(f % size_info)

  dataflow = plan.getDataFlow()
  engine = yaafelib.Engine()
  engine.load(dataflow)
  processor = yaafelib.AudioFileProcessor()

  subsets = { 'full': 'full' }

  def train_pca(pca=None):
    if pca is not None:
        return pca

    assert train_file_path is not None
    print "Training pca..."
    pca = defaultdict(PCA)
    audiofiles_ = glob.glob('%s/*/*.mp3' % train_file_path)
    # extract features from audio files
    for audiofile in audiofiles_:
      processor.processFile(engine, audiofile)
      features = engine.readAllOutputs()
      for subset, keys in subsets.iteritems():
        if keys == 'full':
          keys = sorted(features.keys())
        output = numpy.concatenate([features[k].T for k in keys]).T

#        import ipdb; ipdb.set_trace()
        if 'Train' in audiofile:
            pca[subset].add(output)
    print "PCA training finished."
    return pca

  assert audiofiles is not None
  pca = train_pca(pca)
  assert pca is not None

  for f in features:
    if ':' not in f: f = '%s: %s' % (f, f)
    if '%s' not in f: f += ' %s'
    plan.addFeature(f % size_info)

  # extract features from audio files
  for audiofile in audiofiles:
    audiofile = os.path.join(path, audiofile)
    processor.processFile(engine, audiofile)
    features = engine.readAllOutputs()
    for subset, keys in subsets.iteritems():
      if keys == 'full':
        keys = sorted(features.keys())
      output = numpy.concatenate([features[k].T for k in keys]).T
      pickle_file = audiofile.replace('.mp3', '.%s.pkl' % subset).replace(path, out)
      cPickle.dump(output, file_create(pickle_file), cPickle.HIGHEST_PROTOCOL)

  for subset in subsets.iterkeys():
    pca[subset].pca(diagonal=True)
    cPickle.dump(pca[subset], file_create('%s/%s.pca' % (out, subset)))

  print 'Rewriting PCA data...'
  sys.stdout.flush()

  for audiofile in audiofiles:
    for subset in subsets.iterkeys():
      pickle_file = os.path.join(out, audiofile).replace('.mp3', '.%s.pkl' % subset)
      #pickle_file = audiofile.replace('.mp3', '.%s.pkl' % subset).replace(path, out)
      matrix = cPickle.load(file(pickle_file))
      matrix = pca[subset].feature(matrix)
      cPickle.dump(matrix, file_create(pickle_file.replace('.pkl', '.pca.pkl')), cPickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":

  export_features(train_file_path="/data/lisa/data/faces/EmotiW/audios/Train/",
                  path="/data/lisatmp2/EmotiWTest/audios/",
                  audiofiles=["/data/lisatmp2/EmotiWTest/audios/005242000.mp3"],
                  out="./audio_feats2/")

