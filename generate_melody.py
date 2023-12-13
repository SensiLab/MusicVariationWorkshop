# Copyright 2019 Google LLC.
# Licensed under the Apache License, Version 2.0 (the "License");
# Modification copyright 2020 Bui Quoc Bao
# Change notebook script into package
# Modiication 2022 Stephen Krol
# Created transformer class

import os
import timeit

import tensorflow.compat.v1 as tf  # pylint: disable=import-error

from tensor2tensor.utils import trainer_lib
from tensor2tensor.utils import decoding

import utils

class MagentaMusicTransformer:

    def __init__(self, model_path):

        self.num_samples = 1
        self.decode_length = 1024
        self.problem = utils.MelodyToPianoPerformanceProblem()
        self.model_path = model_path

        # Set up HParams.
        hparams = trainer_lib.create_hparams(hparams_set='transformer_tpu')
        trainer_lib.add_problem_hparams(hparams, self.problem)
        hparams.num_hidden_layers = 16
        hparams.sampling_method = 'random'

        # Set up decoding HParams.
        decode_hparams = decoding.decode_hparams()
        decode_hparams.alpha = 0.0
        decode_hparams.beam_size = 1

        # Create Estimator.
        utils.LOGGER.info('Loading model.')
        run_config = trainer_lib.create_run_config(hparams)
        self.estimator = trainer_lib.create_estimator(
            'transformer', hparams, run_config,
            decode_hparams=decode_hparams
        )
    
    def generate(self, melody_path: str, output_path: str):

        start = timeit.default_timer()
        melody_conditioned_encoders = self.problem.get_feature_encoders()
        melody_ns = utils.get_melody_ns(melody_path)
        inputs = melody_conditioned_encoders['inputs'].encode_note_sequence(melody_ns)

        # date_and_time = time.strftime('%Y-%m-%d_%H%M%S')
        # base_name = '%s_%s-*-of-%03d.mid' % ('melody', date_and_time, self.num_samples)

        for i in range(self.num_samples):
            utils.LOGGER.info('Generating sample %d' % i)
            # Start the Estimator, loading from the specified checkpoint.
            input_fn = decoding.make_input_fn_from_generator(utils.melody_input_generator(
                inputs, self.decode_length))
            melody_conditioned_samples = self.estimator.predict(
                input_fn, checkpoint_path=self.model_path)

            # Generate sample events.
            utils.LOGGER.info('Generating sample.')
            sample_ids = next(melody_conditioned_samples)['outputs']

            # Decode to NoteSequence.
            utils.LOGGER.info('Decoding sample id')
            midi_filename = utils.decode(
                sample_ids,
                encoder=melody_conditioned_encoders['targets'])
            accompaniment_ns = utils.mm.midi_file_to_note_sequence(midi_filename)
            utils.mm.sequence_proto_to_midi_file(accompaniment_ns, output_path)
    

if __name__ == "__main__":

    magenta_transformer = MagentaMusicTransformer("../model/melody_conditioned_model_16.ckpt")
    magenta_transformer.generate("test.mid")

