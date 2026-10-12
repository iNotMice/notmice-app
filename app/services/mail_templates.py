"""Account mail text in the reader's interface language. Only the one-time link varies."""

# Cyrillic letters and typographic apostrophes are the translation itself.
# ruff: noqa: RUF001

from __future__ import annotations

from typing import Final, Literal

from app.domain.locales import MailLocale

MailKind = Literal["confirm", "reset", "lab_confirm", "lab_reset"]

_DEFAULT_LOCALE: Final[MailLocale] = "en"
_LOCALES: Final[dict[str, MailLocale]] = {"en": "en", "ru": "ru", "de": "de", "fr": "fr"}

# (subject, lead line, closing line) per kind and language. The link goes between
# the lead and the validity note; nothing here comes from the request.
_TEXT: Final[dict[MailKind, dict[MailLocale, tuple[str, str, str]]]] = {
    "confirm": {
        "en": (
            "Confirm your NotMice account",
            "To confirm your email address and sign in to NotMice, open this link:",
            "If you did not create a NotMice account, ignore this message.",
        ),
        "ru": (
            "Подтвердите аккаунт NotMice",
            "Чтобы подтвердить почту и войти в NotMice, откройте ссылку:",
            "Если вы не регистрировались в NotMice, просто проигнорируйте это письмо.",
        ),
        "de": (
            "Bestätigen Sie Ihr NotMice-Konto",
            "Um Ihre E-Mail-Adresse zu bestätigen und sich bei NotMice anzumelden, "
            "öffnen Sie diesen Link:",
            "Wenn Sie kein NotMice-Konto erstellt haben, ignorieren Sie diese Nachricht.",
        ),
        "fr": (
            "Confirmez votre compte NotMice",
            "Pour confirmer votre adresse e-mail et vous connecter à NotMice, ouvrez ce lien :",
            "Si vous n’avez pas créé de compte NotMice, ignorez ce message.",
        ),
    },
    "reset": {
        "en": (
            "Reset your NotMice password",
            "To set a new NotMice password, open this link:",
            "If you did not ask to reset your password, ignore this message.",
        ),
        "ru": (
            "Сброс пароля NotMice",
            "Чтобы задать новый пароль NotMice, откройте ссылку:",
            "Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.",
        ),
        "de": (
            "NotMice-Passwort zurücksetzen",
            "Um ein neues NotMice-Passwort festzulegen, öffnen Sie diesen Link:",
            "Wenn Sie kein neues Passwort angefordert haben, ignorieren Sie diese Nachricht.",
        ),
        "fr": (
            "Réinitialisez votre mot de passe NotMice",
            "Pour définir un nouveau mot de passe NotMice, ouvrez ce lien :",
            "Si vous n’avez pas demandé de réinitialisation, ignorez ce message.",
        ),
    },
    "lab_confirm": {
        "en": (
            "Confirm your NotMice laboratory account",
            "To confirm the laboratory email address, open this link and press the button:",
            "If you did not register a laboratory on NotMice, ignore this message.",
        ),
        "ru": (
            "Подтвердите аккаунт лаборатории NotMice",
            "Чтобы подтвердить почту лаборатории, откройте ссылку и нажмите кнопку:",
            "Если вы не регистрировали лабораторию в NotMice, просто проигнорируйте это письмо.",
        ),
        "de": (
            "Bestätigen Sie Ihr NotMice-Laborkonto",
            "Um die E-Mail-Adresse des Labors zu bestätigen, öffnen Sie diesen Link "
            "und drücken Sie die Schaltfläche:",
            "Wenn Sie kein Labor bei NotMice registriert haben, ignorieren Sie diese Nachricht.",
        ),
        "fr": (
            "Confirmez votre compte laboratoire NotMice",
            "Pour confirmer l’adresse e-mail du laboratoire, ouvrez ce lien "
            "et appuyez sur le bouton :",
            "Si vous n’avez pas inscrit de laboratoire sur NotMice, ignorez ce message.",
        ),
    },
    "lab_reset": {
        "en": (
            "Reset your NotMice laboratory password",
            "To set a new password for the laboratory account, open this link:",
            "If you did not ask to reset the password, ignore this message.",
        ),
        "ru": (
            "Сброс пароля лаборатории NotMice",
            "Чтобы задать новый пароль аккаунта лаборатории, откройте ссылку:",
            "Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.",
        ),
        "de": (
            "Passwort des NotMice-Laborkontos zurücksetzen",
            "Um ein neues Passwort für das Laborkonto festzulegen, öffnen Sie diesen Link:",
            "Wenn Sie kein neues Passwort angefordert haben, ignorieren Sie diese Nachricht.",
        ),
        "fr": (
            "Réinitialisez le mot de passe du laboratoire NotMice",
            "Pour définir un nouveau mot de passe du compte laboratoire, ouvrez ce lien :",
            "Si vous n’avez pas demandé de réinitialisation, ignorez ce message.",
        ),
    },
}

_VALIDITY: Final[dict[MailLocale, str]] = {
    "en": "The link works once and is valid for 24 hours.",
    "ru": "Ссылка одноразовая и действует 24 часа.",
    "de": "Der Link funktioniert einmal und ist 24 Stunden gültig.",
    "fr": "Le lien ne fonctionne qu’une fois et reste valable 24 heures.",
}

_SIGNATURE: Final[dict[MailLocale, str]] = {
    "en": "The NotMice team",
    "ru": "Команда NotMice",
    "de": "Das NotMice-Team",
    "fr": "L’équipe NotMice",
}


def mail_locale(value: str | None) -> MailLocale:
    """Return a supported mail language; anything else falls back to English."""
    return _LOCALES.get(value or "", _DEFAULT_LOCALE)


def account_mail(kind: MailKind, locale: str | None, link: str) -> tuple[str, str]:
    """Build the subject and plain-text body for one account link.

    Args:
        kind: Which link the message carries.
        locale: Interface language of the person who asked; unknown values use English.
        link: The one-time link, built by the caller from the configured app URL.

    Returns:
        ``(subject, body)``.
    """
    language = mail_locale(locale)
    subject, lead, closing = _TEXT[kind][language]
    body = f"{lead}\n{link}\n\n{_VALIDITY[language]}\n{closing}\n\n— {_SIGNATURE[language]}\n"
    return subject, body
