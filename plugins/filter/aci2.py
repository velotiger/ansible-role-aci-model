# Copyright: (c) 2020-2023, Tilmann Boess <tilmann.boess@hr.de>
# Based on: (c) 2017, Ramses Smeyers <rsmeyers@cisco.com>

# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
This module provides enhanced filters to the original 'aci_listify' (module
'aci.py'). The instances (e.g. tenant, vrf, leafid, …) can be organized in a
dict as well as in a list. If you need to lookup instances directly (e.g. by
other filters), it might be useful to organize your inventory in dicts instead
of lists.

*** Examples for filter 'aci_listify2' ***

1. Simple static specification:
  loop: "{{ aci_topology|aci_listify2('access_policy', 'interface_policy_profile=.+998', 'interface_selector') }}"
All paths in the output match interface policy profiles that end in «998».
E.g. interface selectors below a non-matching interface policy profile
will be suppressed from the output.
2. Dynamic specification:
  loop: "{{ LEAFID_ROOT|aci_listify2(leaf_match, port_match, 'type=switch_port') }}"
  vars:
    leaf_match: "leafid={{ outer.leafid_Name }}"
    port_match: "port={{ outer.leafid_port_Name }}"
Here the regex's for the leafid and the port are determined at runtime in an
outer task. The outer task sets the dict 'outer' and this dict is referenced
here.
'LEAFID_ROOT' is the dict in which to look for the following hierarchy:
  leafid:
  # leafid 101: all instances organized in lists.
  - Name: 101
    port:
    - Name: 1
      type:
      - Name: vpc
    - Name: 2
      type:
      - Name: port_channel
    - Name: 3
      type:
      - Name: switch_port
  - Name: 102
    # leafid 102: organized in dicts and lists.
    port:
      # port instances: dict
      1:
        Name: 1
        type:
          # type instances: dict
          vpc:
            Name: vpc
      2:
        Name: 2
        type:
          # type instances: dict
          port_channel:
            Name: port_channel
      4:
        Name: 4
        type:
        # type instances: list
        - Name: switch_port
( … and so on for all leaf-switches and ports …)
This matches only if:
* leafid matches the leafid delivered by the outer task.
* port matches the port delivered by the outer task.
* The port shall be configured as a simple switchport (not a channel).
The outer task could be:
  - name: "example outer task"
    include_tasks:
      file: inner.yaml
    loop: "{{ portlist }}"
    loop_control:
      loop_var: outer
    vars:
      portlist:
      - leafid_Name: '10.'
        leafid_port_Name: '3'
      - leafid_Name: '.0.'
        leafid_port_Name: '(2|4)'
The dict 'portlist' need not be specified here as task variable.
You can provide it as extra var on the command line and thus specify
dynamically which ports shall be configured.

*** Filter super_listify2 – to be written ***

This filter replaces both the outer an the inner task in example 2 above.
The output is a list in the same format as above with all matching items.
Example usage:
  loop: "{{ LEAFID_ROOT|super_listify2(portlist, 'type=switch_port') }}"
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re

# Global variables:
# * Name of the attribute used as «Name». We use uppercase «Name» to
#   let it appear 1st if YAML/JSON files are sorted by keys.
#   Change it to your liking.
nameAttr = 'Name'
# * Regex to separate object and instance names.
rValue = re.compile('([^=]+)=(.*)')
# * Regex to extract object type name from flattened key name, e.g.
#   leafid_port_Name → port
rSuper = re.compile('%s_%s' % (r'.*?_?([a-zA-Z0-9]+)', nameAttr))


def lister(myDict, *myKeys):
    """Extract key/value data from ACI-model object tree.
The keys must match dict names along a path in this tree down to a dict that
contains at least 1 key/value pair.
Along this path all key/value pairs for all keys given are fetched.
Args:
* myDict (dict): object tree.
* *myKeys: key names to look for in 'myDict' in hierarchical order (the keys
must form a path in the object tree).
* You can append a regex to each key (separated by «=»). Only keys
whose name-attribute matches the regex will be included in the result.
If the regex is omitted, all keys will be included (backwards compatible).
Returns:
* list of dicts (key/value-pairs); given keys are concatenated with '_' to form
a single key. Example: ('tenant' , 'app' , 'epg') results in 'tenant_app_epg'.
"""
    # keyList will be a copy of the initial list «myKeys».
    keyList = []
    # List of regex to match the name attributes.
    regexList = []
    for K in myKeys:
        match = rValue.fullmatch(K)
        if match:
            keyList.append(match.group(1))
            regexList.append(re.compile(match.group(2)))
        else:
            keyList.append(K)
            regexList.append(None)

    def worker(itemList, depth, result, cache, prefix):
        """Inner function for instance evaluation.
Args:
* itemList (list): current instance list in tree (list of dicts, each item
is an ACI object).
* depth (int): index (corresponding to depth in object tree) of key in key list.
* result (list): current result list of key/value-pairs.
* cache (dict): collects key/value pairs common for all items in result list.
* prefix (str): current prefix for key list in result.
"""
        for item in itemList:
            # Save name attribute for later usage.
            # If name attribute is missing, set to None.
            name = str(item.get(nameAttr, None))
            # cache holds the pathed keys (build from the key list).
            # Each recursive call gets its own copy.
            subcache = cache.copy()
            for subKey, subItem in list(item.items()):
                if isinstance(subItem, (str, int, float, bool, bytes)) or isinstance(subItem, list) and all(isinstance(x, (str, int, float, bool, bytes)) for x in subItem):
                    # Key/value found. Accept a scalar or a list of scalars as attribute value.
                    subcache['%s%s' % (prefix, subKey)] = subItem
                    # All key/value pairs are evaluated before dicts and lists.
                    # Otherwise, some attributes might not be transferred from the
                    # cache to the result list.
            if regexList[depth] is not None and (name is None or not regexList[depth].fullmatch(name)):
                # If regex was specified and the nameAttr does not match, do
                # not follow the path but continue with next item. Also a
                # non-existing nameAttr attribute is interpreted as non-match.
                continue
            result = finder(item, depth, result, subcache, prefix)
        return result

    def finder(objDict, depth=-1, result=None, cache=None, prefix=''):
        """Inner function for tree traversal.
* objDict (dict): current subtree, top key is name of an ACI object type.
* depth (int): index (corresponding to depth in object tree) of key in key list.
* result (list): current result list of key/value-pairs.
* cache (dict): collects key/value pairs common for all items in result list.
* prefix (str): current prefix for key list in result.
"""
        if result is None:
            result = []
        if cache is None:
            cache = {}
        depth += 1
        if depth == len(keyList):
            # At end of key list: transfer cache to result list.
            result.append(cache)
        else:
            prefix = ''.join((prefix, keyList[depth], '_'))
            # Check if object type is in tree at given depth.
            if keyList[depth] in objDict:
                # Prepare item list. ACI objects may be stored as list or dict.
                if isinstance(objDict[keyList[depth]], list):
                    itemList = objDict[keyList[depth]]
                elif isinstance(objDict[keyList[depth]], dict):
                    itemList = list(objDict[keyList[depth]].values())
                else:
                    # Neither dict nor list – return to upper level.
                    return result
                result = worker(itemList, depth, result, cache.copy(), prefix)
        return result

    # End of function: lister
    return finder(myDict)


def superlister(myDict, *myList):
    """Prepare input lists for lister, feed these lists to lister and return
a single list of the items matching the specifications of the input.
"""
    if myList[0] == []:
        # Avoid a useless search for an empty input list.
        resultList = []
    else:
        inputList = []
        # The 1st item is a list of dicts: search specification for objects in the
        # inventory tree.
        for item in myList[0]:
            inputList.append([])
            for key, value in item.items():
                # Extract object type name.
                m = rSuper.fullmatch(key)
                if m:
                    inputList[-1].append('%s=%s' % (m.group(1), value))
        resultList = []
        for listItem in inputList:
            # Append exceeding items so that the lister will output their attribs.
            listItem.extend(myList[1:])
            resultList.extend(lister(myDict, *listItem))
    return resultList


class FilterModule(object):
    """Jinja2 filters for Ansible."""

    def filters(self):
        """Define ACI listify filters."""
        return {
            'aci_listify2': lister,
            'super_listify2': superlister
        }
