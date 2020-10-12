from subprocess import getoutput  # skipcq: BAN-B404

import requests

VERSION = getoutput("git describe").lstrip("v")
MORPHEUS_ICON = "https://cdn.discordapp.com/avatars/686299664726622258/cb99c816286bdd1d988ec16d8ae85e15.png"
CONTRIBUTORS = [
    212866839083089921,
    137906177487929344,
    306774624090456075,
    339062431131369472,
    541341790176018432,
    330148908531580928,
]
GITHUB_LINK = "https://github.com/Defelo/MorpheusHelper"
AVATAR_URL = "https://github.com/Defelo.png"
GITHUB_DESCRIPTION = requests.get("https://api.github.com/repos/Defelo/MorpheusHelper").json()["description"]
