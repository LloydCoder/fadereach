# Web Security Headers

The production edge/application should use a considered Content-Security-Policy, HSTS where TLS is enforced, X-Content-Type-Options, Referrer-Policy and frame protections.

Headers must be tested against actual application behavior rather than copied blindly from templates. Cookies should use Secure, HttpOnly and SameSite settings appropriate to their purpose.