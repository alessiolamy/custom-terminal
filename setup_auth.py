#!/usr/bin/env python3
"""
setup_auth.py — Run once locally to generate your auth credentials.
Outputs values to paste into .streamlit/secrets.toml or GitHub Secrets.

Usage:
    python setup_auth.py
"""

import hashlib
import pyotp
import qrcode          # pip install qrcode[pil]  (optional, for QR display)
import sys

def main():
    print("\n" + "═"*55)
    print("  BLOOMBERG TERMINAL — Auth Setup")
    print("═"*55 + "\n")

    # 1. Password
    pw = input("Choose a password: ").strip()
    if not pw:
        print("Password cannot be empty.")
        sys.exit(1)
    pw_hash = hashlib.sha256(pw.encode()).hexdigest()
    print(f"\n✓ APP_PASSWORD_HASH = \"{pw_hash}\"")

    # 2. TOTP
    secret = pyotp.random_base32()
    totp   = pyotp.TOTP(secret)
    label  = input("\nYour name / label for authenticator app [Me]: ").strip() or "Me"
    uri    = totp.provisioning_uri(name=label, issuer_name="BB Terminal")

    print(f"\n✓ TOTP_SECRET = \"{secret}\"")
    print(f"\n📱 Scan this URI in Google Authenticator / Authy:")
    print(f"   {uri}\n")

    # Try to show QR in terminal
    try:
        import qrcode as qr
        qr_img = qr.make(uri)
        # Print as ASCII if possible
        try:
            import qrcode.image.svg
            print("(Install 'qrcode[pil]' and run again for a QR image)")
        except Exception:
            pass
        qr_img.save("totp_qr.png")
        print("✓ QR code saved to totp_qr.png — open and scan it.")
    except ImportError:
        print("  pip install qrcode[pil]  to auto-generate a QR image.")

    # 3. Summary
    print("\n" + "─"*55)
    print("Paste these into .streamlit/secrets.toml:\n")
    print(f'APP_PASSWORD_HASH = "{pw_hash}"')
    print(f'TOTP_SECRET       = "{secret}"')
    print("\nAlso add your FRED API key and any other keys.")
    print("─"*55 + "\n")

if __name__ == "__main__":
    main()
