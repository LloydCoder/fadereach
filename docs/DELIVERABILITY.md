# Deliverability Control Plane

FadeReach measures observable sender readiness; it does not promise inbox placement.

## Controls
Track SPF, DKIM, DMARC, forward/reverse DNS/PTR, TLS, RFC-compliant formatting, bounce rate, complaint/spam rate, unsubscribe/suppression, sending volume/rate, provider/mailbox health and reputation signals where available.

## Provider baseline
Google's current sender guidance requires SPF or DKIM for all senders and stronger requirements for bulk senders, including SPF+DKIM+DMARC, valid DNS/PTR, TLS, low spam rates, DMARC alignment for direct mail and one-click unsubscribe for marketing/subscribed messages.

Provider requirements change independently of this repository and must be revalidated before policy changes.

## Controls
Below-policy readiness should reduce or prevent sending. Suppression, complaint and hard-bounce signals are hard execution constraints.