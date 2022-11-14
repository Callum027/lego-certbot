# lego-certbot

A compatibility script between [Lego](https://go-acme.github.io/lego) and [Certbot](https://certbot.eff.org), to allow Lego to use Certbot authenticator plugins to perform `DNS-01` challenges.

Designed to be run using the [exec](https://go-acme.github.io/lego/dns/exec/) provider in `default` mode.

## Installing

`lego-certbot` can be directly installed using `pip`.

Available extras:

* `metaname` - install the [certbot-dns-metaname](https://github.com/Callum027/certbot-dns-metaname/tree/stateless-cleanup) DNS authenticator

```
$ python3 -m pip install "lego-certbot @ https://github.com/Callum027/lego-certbot/archive/refs/tags/v0.1.0.zip"
```

The repository contains a fixed `requirements.txt` with known working package versions, and a virtual environment can be created based on that.

```
$ git clone -b v0.1.0 https://github.com/Callum027/lego-certbot.git
$ cd lego-certbot
$ python3 -m .venv
$ source .venv/bin/activate
$ python3 -m pip install -r requirements.txt .
```

Or, if you have Poetry installed, you can setup the virtual environment using `poetry install`.

```
$ git clone -b v0.1.0 https://github.com/Callum027/lego-certbot.git
$ cd lego-certbot
$ poetry install [--with=metaname]
```

## Configuration

Configuration of the Lego `exec` provider is done via [environment variables](https://go-acme.github.io/lego/dns/exec/#base-configuration).

Base configuration:

* `EXEC_PATH` - Path to the script (e.g. `/usr/local/bin/lego-certbot`)

`EXEC_MODE` must be undefined, or oteherwise not set to `RAW` mode.

Additional configuration used by the script:

* `EXEC_POLLING_INTERVAL` - Time between DNS propagation checks, in seconds.\
  Default: `5`
* `EXEC_PROPAGATION_TIMEOUT` - Maximum waiting time for DNS propagation, in seconds. Used to set `propagation_seconds` in the Certbot authenticator plugin.\
  Default: (plugin default)

As Lego's `exec` provider enforces a standard interface for the script itself, configuration cannot be done via the command line.

```
$ poetry run lego-certbot --help
usage: lego-certbot [-h] {present,cleanup,timeout} [fqdn] [record]

Glue script between Lego and Certbot, to allow Lego to use Certbot authenticator plugins to perform DNS-01 challenges.
Designed to be run using the 'exec' provider in 'default' mode.

positional arguments:
  {present,cleanup,timeout}
                        ACME challenge command type
  fqdn                  Domain name (including subdomain) to use for the ACME challenge
  record                TXT record challenge response value

optional arguments:
  -h, --help            show this help message and exit
```

Instead, `lego-certbot` itself is configured using the following environment variables.\
It also shows an configuration for [the third party Metaname DNS authenticator](https://github.com/Callum027/certbot-dns-metaname/tree/stateless-cleanup) as an example of how to use them.

* `LEGOCERTBOT_AUTHENTICATOR_TYPE` - The [DNS authenticator plugin](https://eff-certbot.readthedocs.io/en/stable/using.html#dns-plugins) to use.\
   Example: `dns-metaname`

* `LEGOCERTBOT_AUTHENTICATOR_CONFIG` - Parameters to pass to the authenticator, in JSON format.
  Example: `{"endpoint":"https://metaname.net/api/1.1","credentials":"/etc/traefik/metaname.ini"}`

## Usage

### Lego

A complete invocation of Lego would look something like this.

```bash
EXEC_PATH="/usr/local/bin/lego-certbot" \
EXEC_POLLING_INTERVAL=5 \
EXEC_PROPAGATION_TIMEOUT=120 \
LEGOCERTBOT_AUTHENTICATOR_TYPE="dns-metaname" \
LEGOCERTBOT_AUTHENTICATOR_CONFIG='{"endpoint":"https://metaname.net/api/1.1","credentials":"/etc/traefik/metaname.ini"}' \
lego --email you@example.com --dns exec --domains example.com run
```

### Traefik

This example shows how `lego-certbot` can be used with Traefik to generate wildcard certificates for all services under a root domain.

[Static configuration](https://doc.traefik.io/traefik/getting-started/configuration-overview/#the-static-configuration) (`traefik.yml`):
```yaml
# Reverse proxy entrypoints.
# (Not relevant to the example)
entryPoints:
  # HTTP entrypoint.
  # Automatically redirect HTTP to HTTPS.
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
  # HTTPS entrypoint.
  websecure:
    address: ":443"

# Certificate resolvers, used to generate TLS certificates for routers.
# In this case, we're using Let's Encrypt to generate certificates via the DNS-01 challenge.
certificatesResolvers:
  letsencrypt:
    acme:
      # Email address to send to Let's Encrypt.
      email: you@example.com
      # Path to save ACME certification files to.
      # (Paths are resolved relative to the pwd of the Traefik process.)
      storage: acme.json
      # DNS-01 challenge configuration.
      dnsChallenge:
        # Lego DNS provider to use.
        provider: exec
        # Authoritative nameservers for the DNS provider to check against.
        # In this example, these are Metaname's servers.
        resolvers:
          - "49.50.242.204:53"
          - "103.11.126.252:53"
          - "103.11.126.244:53"
      # During development, uncomment the following line to use the Let's Encrypt staging server.
      # Necessary to avoid hitting the rate limits on the production servers.
      # caServer: https://acme-staging-v02.api.letsencrypt.org/directory
```

[Dynamic configuration](https://doc.traefik.io/traefik/getting-started/configuration-overview/#the-dynamic-configuration) (`file` provider):
```yaml
# Example router/service which receives a wildcard certificate
# from the Let's Encrypt certificate resolver.
http:
  routers:
    whoami:
      rule: "Host(`whoami.example.com`)"
      service: whoami
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt
        domains:
          - main: "example.com"
            sans: "*.example.com"
  services:
    whoami:
      loadBalancer:
        servers:
          - url: "http://192.0.2.1:8080/"
```
