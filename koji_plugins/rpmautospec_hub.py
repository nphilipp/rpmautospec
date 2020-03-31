import logging
import re

import koji
from koji.plugin import callback
import requests

from rpmautospec.py2compat import tagging


CONFIG_FILE = "/etc/koji-hub/plugins/rpmautospec_hub.conf"
CONFIG = None

_log = logging.getLogger("koji.plugin.rpmautospec_hub")


@callback("postTag")
def autotag_cb(cb_type, **kwargs):
    global CONFIG

    if not CONFIG:
        try:
            CONFIG = koji.read_config_files([(CONFIG_FILE, True)])
        except Exception:
            message = "While attempting to read config file %s, an exception occurred:"
            _log.exception(message, CONFIG_FILE)
            return

    base_url = CONFIG.get("pagure", "url")
    token = CONFIG.get("pagure", "token")

    git_filter = r".*\.fedoraproject\.org/(?P<repo>rpms/.*)\.git#(?P<commit>[a-f0-9]{40})$"
    if CONFIG.has_option("pagure", "git_filter"):
        git_filter = CONFIG.get(
            "pagure",
            "git_filter",
        )
    git_filter_re = re.compile(git_filter)

    build = kwargs["build"]

    if build.get("source"):
        match = re.match(git_filter_re, build["source"])
        repo = match.group("repo")
        commit = match.group("commit")
        if not repo or not commit:
            info = "Could not parse repo and commit from {}, skipping."
            _log.info(info.format(build["source"]))
            return
    else:
        _log.info("No source for this build, skipping.")
        return

    build["epoch"] = build.get("epoch") or 0

    nevr = "{name}-{epoch}-{version}-{release}".format(**build)

    if not build["epoch"]:
        nevr = "{name}-{version}-{release}".format(**build)

    escaped_nevr = tagging.escape_tag(nevr)

    data = {
        "tagname": escaped_nevr,
        "commit_hash": commit,
        "message": None,
        "with_commits": True,
    }

    endpoint_url = "{}/api/0/{}/git/tags".format(base_url, repo)
    headers = {"Authorization": "token {}".format(token)}
    try:
        response = requests.post(endpoint_url, headers=headers, data=data)
    except Exception:
        error = "While attempting to create a tag in %s, an exception occurred:"
        _log.exception(error, endpoint_url)
        return

    if not response.ok:
        error = "While attempting to create a tag in %s, the request failed with: STATUS %s %s"
        _log.error(error, endpoint_url, response.status_code, response.text)
        return
