#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# lego-certbot
# A compatibility script between Lego and Certbot, to allow Lego to
# use Certbot authenticator plugins to perform DNS-01 challenges.
# Designed to be run using the 'exec' provider in 'default' mode.


from __future__ import annotations

import json
import os
import sys

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Type

    from certbot.interfaces import DNSAuthenticator


__version__ = "0.2.0"


def main() -> int:
    """
    lego-certbot main routine.
    """

    # Parse arguments passed from Lego.
    # This follows a common standard defined here:
    #   https://go-acme.github.io/lego/dns/exec/
    arg_parser = ArgumentParser(
        description=(
            "A compatibility script between Lego and Certbot, to allow Lego to "
            "use Certbot authenticator plugins to perform DNS-01 challenges.\n"
            "Designed to be run using the 'exec' provider in 'default' mode."
        ),
        formatter_class=RawTextHelpFormatter,
    )
    arg_parser.add_argument(
        "command",
        choices=["present", "cleanup", "timeout"],
        help="ACME challenge command type",
    )
    arg_parser.add_argument(
        "name",
        type=str,
        nargs="?",
        default=None,
        help="ACME challenge TXT record name (e.g. _acme-challenge.example.com)",
    )
    arg_parser.add_argument(
        "value",
        type=str,
        nargs="?",
        default=None,
        help="ACME challenge TXT record value",
    )
    arg_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = arg_parser.parse_args()

    # Get the command to execute.
    command: str = args.command

    # Root domain name under which the TXT record will be propagated.
    domain = os.environ["LEGOCERTBOT_DOMAIN"]

    # Get the authenticator configuration from environment variables.
    # Authenticator type, as specified to Certbot.
    # (Example: certbot-dns-metaname:dns-metaname)
    authenticator_type = os.environ["LEGOCERTBOT_AUTHENTICATOR_TYPE"]

    # Get the authenticator's module name and configuration prefix.
    authenticator_module_name = authenticator_type
    authenticator_config_prefix = authenticator_module_name.replace("-", "_")

    # Read in the authenticator configuration as a JSON object
    # from the LEGOCERTBOT_AUTHENTICATOR_CONFIG environment variable.
    # EXEC_PROPAGATION_TIMEOUT is also read and used to set its
    # Certbot equivalent here.
    authenticator_config = Namespace(
        **{
            **{
                f"{authenticator_config_prefix}_propagation_seconds": int(
                    os.environ.get("EXEC_PROPAGATION_TIMEOUT", 120),
                ),
            },
            **{
                f"{authenticator_config_prefix}_{name}": value
                for name, value in json.loads(
                    os.environ.get("LEGOCERTBOT_AUTHENTICATOR_CONFIG", "{}"),
                ).items()
            },
        },
    )

    # Interval to test DNS propagation, in seconds. (Default: 5)
    interval = int(os.environ.get("EXEC_POLLING_INTERVAL", 5))

    # Read the Certbot plugin entry points to find the authenticator's entry,
    # and import the class directly.
    # Note: importlib.metadata was a provisional library from
    #       Python 3.8 until Python 3.10, and the original
    #       entrypoint querying method was deprecated from 3.10 onwards.
    if sys.version_info >= (3, 10):
        (authenticator_ep,) = entry_points(
            group="certbot.plugins",
            name=authenticator_module_name,
        )
        authenticator_class: Type[DNSAuthenticator] = authenticator_ep.load()
    else:
        authenticator_class = [
            ep for ep in entry_points()["certbot.plugins"] if ep.name == authenticator_module_name
        ][0].load()

    # Create an authenticator object to operate against.
    authenticator = authenticator_class(authenticator_config, authenticator_config_prefix)

    # For the 'timeout' command, return the configured timeout and
    # poll interval as a JSON object.
    # https://go-acme.github.io/lego/dns/exec/#timeout
    if command == "timeout":
        print(
            json.dumps(
                {
                    "timeout": authenticator.conf("propagation-seconds"),
                    "interval": interval,
                },
            ),
        )
        sys.exit(0)

    # Parse the ACME challenge record name and value and generate
    # parameters that the Certbot DNS authenticator will accept.
    for arg in ("name", "value"):
        if not getattr(args, arg):
            raise ValueError(f"Argument '{arg}' is required for command '{command}'")
    validation_domain: str = args.name.rstrip(".")
    validation: str = args.value

    # Read the credentials required to access the authenticator's API.
    authenticator._setup_credentials()

    # Execute the specified command.
    if command == "present":
        authenticator._perform(domain, validation_domain, validation)
    elif command == "cleanup":
        authenticator._cleanup(domain, validation_domain, validation)
    else:
        raise ValueError(f"Unsupported ACME challenge command type '{command}'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
