<img src="icon.png" alt="" width="88" align="right">

# MrPatates' Unraid templates

[Français](README.fr.md)

This repository publishes the Unraid Community Applications templates of MrPatates' apps. It is the single repository registered in Community Applications. Each app keeps its code, documentation, issue tracker and template source in its own repository.

| App | Type | Source and support |
| --- | --- | --- |
| **Endfield-Check-in**: automatic SKPORT daily check-in for Arknights: Endfield | Docker | [MrPatates/endfield-checkin](https://github.com/MrPatates/endfield-checkin) |
| **THERMALRIGHT DIGITAL**: Thermalright Peerless Assassin 140 Digital display driver | Plugin | [MrPatates/thermalright-digital-unraid](https://github.com/MrPatates/thermalright-digital-unraid) |

Install them from the **Apps** tab of Unraid. Report problems in each app's own repository.

## How it works

- [`sources.json`](sources.json) lists where each template comes from.
- The **Sync templates** workflow runs every 6 hours, or on demand from the Actions tab. It copies each template from its app repository, rewrites `<TemplateURL>` for Docker templates so that it points to the copy here, validates everything and commits the changes.
- Do not edit `templates/` or `plugins/` by hand: change the template in the app repository, then run **Sync templates**.
- [`scripts/validate.py`](scripts/validate.py) checks the Community Applications requirements: XML structure, required fields, `TemplateURL`, unique names, masked secrets and `ca_profile.xml`. With `--online`, it also checks that every link answers and every Docker image can be pulled anonymously.

To add an app, add an entry to `sources.json`, then run `python3 scripts/sync.py && python3 scripts/validate.py --online`.

GitHub disables scheduled workflows after 60 days without activity in a public repository. If that happens, re-enable **Sync templates** in the Actions tab.

License: MIT for this repository. Each app has its own license.
