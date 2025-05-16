import enum


class AuthProvider(enum.Enum):
    local = "local"
    vk = "vk"
    google = "google"
