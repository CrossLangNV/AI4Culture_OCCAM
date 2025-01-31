import configparser
import os
import unittest

from configs.parser import configuration_pero_ocr, config_parser_to_dict, ROOT

layout_model_name = 'test_layout_model'
ocr_model_name = 'test_ocr_model'
image_folder_name = ''  # TODO?


class TestConfigs(unittest.TestCase):
    def test_foo(self):

        config = configuration_pero_ocr('',
                                        layout_model_name,
                                        ocr_model_name,
                                        )

        d_config = config_parser_to_dict(config)

        config_read = configparser.ConfigParser()
        config_read.read(os.path.join(ROOT, 'configs/test.config'))

        d_config_read = config_parser_to_dict(config_read)

        for key, value in d_config.items():

            value_read = d_config_read.get(key, {})

            for key_sub, value_sub in value.items():
                with self.subTest(f'[{key}] : {key_sub}'):
                    value_read_sub = value_read.get(key_sub)

                    self.assertEqual(value_sub, value_read_sub, 'Should contain same information')
