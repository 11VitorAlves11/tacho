# Security policy

Only the latest stable Tacho release receives security fixes.

Please do not open a public issue for a suspected vulnerability. Use GitHub's
private vulnerability reporting for this repository. If that feature is not
available, contact the maintainer privately through the address published on
the maintainer's GitHub profile and include a way to reply securely.

Include the affected version, deployment model, reproduction steps, impact and
any known mitigations. Do not access data that is not yours and do not perform
denial-of-service testing against third-party installations.


## Recipe import by URL

Fetching a user-supplied URL happens on the server (Celery worker), so the
import pipeline enforces a strict outbound policy (`backend/app/remote_fetch.py`):

- only `http`/`https` URLs whose hostname resolves exclusively to public
  addresses; private, loopback, link-local, reserved, multicast and unspecified
  ranges are rejected, including IPv4 addresses embedded in IPv6
  (`::ffff:127.0.0.1`, 6to4);
- redirects are never followed automatically: at most 5 hops, each one
  validated again before it is requested;
- the TCP connection is made to the address that was just validated, so a DNS
  answer cannot change between the check and the connection (DNS rebinding);
  the original hostname is still used for the `Host` header, TLS SNI and
  certificate verification;
- proxy environment variables are ignored for these requests, because a proxy
  would connect on the server's behalf and bypass the address check;
- connect/read timeouts, a 30-second download deadline, a 5 MB limit for HTML
  (the configured image limit for photos) and an allow-list of content types;
  the import task itself has a 60-second soft / 90-second hard time limit;
- `recipe-scrapers` only parses the downloaded HTML and never fetches by itself.

The import status endpoint only reveals the created recipe to the workspace that
requested it and never returns the worker's exception text; details are logged
server-side.

Residual risk: the policy cannot protect services that are reachable through a
public address (for example a public IP of the host itself, or a NAT64 prefix
that maps to internal IPv4 networks). Restrict worker egress at the network
level if such services exist.
