import unittest

from command_api_config import load_command_api_config


class CommandApiConfigTest(unittest.TestCase):
    def test_defaults_to_disabled(self):
        config = load_command_api_config({})

        self.assertFalse(config.enabled)
        self.assertIsNone(config.token)
        self.assertEqual(config.host, "127.0.0.1")

    def test_allows_enabled_loopback_configuration(self):
        config = load_command_api_config(
            {
                "HEXSTRIKE_COMMAND_API_ENABLED": "true",
                "HEXSTRIKE_COMMAND_API_TOKEN": "secret",
                "HEXSTRIKE_HOST": "localhost",
            }
        )

        self.assertTrue(config.enabled)
        self.assertTrue(config.accepts_token("secret"))
        self.assertFalse(config.accepts_token("wrong"))

    def test_rejects_enabled_configuration_without_token(self):
        for token in (None, "", "  "):
            with self.subTest(token=token):
                environment = {"HEXSTRIKE_COMMAND_API_ENABLED": "true"}
                if token is not None:
                    environment["HEXSTRIKE_COMMAND_API_TOKEN"] = token
                with self.assertRaisesRegex(ValueError, "TOKEN is required"):
                    load_command_api_config(environment)

    def test_rejects_non_loopback_host_when_enabled(self):
        for host in ("0.0.0.0", "192.0.2.1", "::1"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, "must be 127.0.0.1 or localhost"):
                    load_command_api_config(
                        {
                            "HEXSTRIKE_COMMAND_API_ENABLED": "true",
                            "HEXSTRIKE_COMMAND_API_TOKEN": "secret",
                            "HEXSTRIKE_HOST": host,
                        }
                    )

    def test_rejects_invalid_enablement_value(self):
        with self.assertRaisesRegex(ValueError, "must be a boolean"):
            load_command_api_config({"HEXSTRIKE_COMMAND_API_ENABLED": "sometimes"})


if __name__ == "__main__":
    unittest.main()
