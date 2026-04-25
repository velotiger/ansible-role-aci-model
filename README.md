<!---
File: README.md for repo ansible-role-aci-model
--->

***This repo has been migrated to Codeberg: https://codeberg.org/velotiger/ansible-role-aci-model<br>***
*The old repo https://github.com/velotiger/ansible-role-aci-model on GitHub was archived on 2026-04-25.*

# Ansible listify filters for Cisco ACI

This is a fork of [GitHub datacenter/aci-model](https://github.com/datacenter/ansible-role-aci-model).
That repo contains an Ansible role to deploy Cisco ACI fabrics and an Ansible filter plugin.
The filter is not limited to Cisco ACI and does not depend on this Ansible role.
It can be used in any Ansible task to extract a list of items from a structured dict.
For this purpose, it suffices to install the filter.
Neither the role nor the playbook or the example inventory are needed.
Because of its general usefulness, [Ansible collection cisco.aci](https://github.com/CiscoDevNet/ansible-aci) from
[v2.9.0](https://github.com/CiscoDevNet/ansible-aci/releases/tag/v2.9.0) onwards includes the original filter plugin.

This repo focuses on the filter and contains almost no alterations to the role (save some minor fixes).
For a description of the role, refer to the original [README.md](ansible-role-aci-model.md).

## Install the aci filter plugins

You need to configure your Ansible to find the Jinja2 filters. There are two ways to do this:

1. Add the directory `plugins/filter` of this repo to your Ansible configuration file (use `ansible --version` to find its location):<br>
`filter_plugin = ~/ansible-role-aci-model/plugins/filter`
2. Copy the filter plugin files (`plugins/filter/aci*.py`) into your designated Ansible filter plugin directory.

## Improvements to the filter plugin

The file [`plugins/filter/aci2.py`](plugins/filter/aci2.py) contains two filter definitions:

* The alternative filter *aci_listify2* provides the following enhancements:
  * Instances of objects can be organized in lists (as in the original filter) or dicts (new).
  * You can append a regex to each key so that only key values that match the regex will appear in the output.
  * This is documented in the file itself.
* The additional filter *super_listify2* can be used instead of a loop task to feed the filter *aci_listify2*.

The file [`plugins/filter/aci.py`](plugins/filter/aci.py) contains the simple filter *aci_listify1* (same functionality as the original filter, no regex support).
It has been renamed in order to avoid a name clash with the filter *aci_listify* distributed in the collection cisco.aci.
You can safely use the filter *aci_listify2* instead; if no regex is supplied, it works like the simple filter.

## License

GPLv3