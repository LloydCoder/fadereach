# Deliverability Control Plane

## Principle

FadeReach measures observable sender readiness; it does not promise inbox placement.

## Required controls

Track:
- SPF
- DKIM
- DMARC
- forward/reverse DNS/PTR
- TLS
- RFC-compliant message formatting
- bounce rate
- complaint/spam rate
- unsubscribe/suppression
- sending volume/rate
- provider/mailbox health
- domain/IP reputation signals where available

## Provider baseline

Google's current sender guidance requires SPF or DKIM for all senders and stronger requirements for bulk senders, including SPF+DKIM+DMARC, valid DNS/PTR, TLS, low spam rates, DMARC alignment for direct mail and one-click unsubscribe for marketing/subscribed messages.

The system MUST treat provider rules as changing external constraints and link policy updates to the current provider documentation.

## Control behavior

When readiness is below policy threshold, the platform should prevent or reduce sending rather than inventing a confidence score that implies delivery certainty.

## Suppression

Unsubscribe, complaint, hard-bounce and policy suppression signals MUST be evaluated before sending. Suppression is a hard execution constraint, not a recommendation.