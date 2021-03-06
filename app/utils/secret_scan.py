#!/bin/python3

import os
import json
import sys
import re
import string
import yaml


# Taken directly from TruffleHog
# https://github.com/dxa4481/truffleHog/blob/0f223225d6efc8c64504d9381eececb06b14c0e6/truffleHog/truffleHog.py#L120-L138
# Therefore GPL Licensed

import math

BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
HEX_CHARS = set("1234567890abcdefABCDEF")
ASCII_CHARS = set(string.printable)

MAX_ENTROPY = float(os.getenv('MAX_ENTROPY', default=3.5))

SAFE_ENDINGS = [
    'apiVersion',   # High entropy
    'name',         # Env vars
    'image',        # Images and registries have high entropy
    'description',  # Argo specific, long human description
    'template',     # Argo specific, references parts of the DAG by name
    'entrypoint',
    'pipelines.kubeflow.org/pipeline_compilation_time',
    'path',
    'workingDir',
    'kind',
    'digest',
    'onExit'
]
SAFE_ENDINGS = [x.lower() for x in SAFE_ENDINGS]

MASK_ON = False
MASK_LEN = 8

# Very basic regexp to filter out internal kubernetes services.
URL_REGEXP = re.compile("https?:\/\/[a-zA-Z0-9][a-zA-Z0-9-\.]+(:[0-9][0-9]+)?$")


def shannon_entropy(data, iterator):
    """
    Borrowed from http://blog.dkbza.org/2007/05/scanning-data-for-entropy-anomalies.html
    """
    if not data:
        return 0
    entropy = 0
    for x in iterator:
        p_x = float(data.count(x))/len(data)
        if p_x > 0:
            entropy += - p_x*math.log(p_x, 2)
    return entropy




# Borrowed from @wg102
# https://github.com/wg102/kubeflow_pipeline_detection

def seq_iter(obj):
    if isinstance(obj, dict):
        return obj.items()
    elif isinstance(obj, list):
        return enumerate(obj)
    else:
        print(f"WARNING: '{obj}' is neither a dict not a list. Skipping", file=sys.stderr)
        return [obj]

def traversal(tree, parent=[]):
    """
    Get all (key, value) pairs in the object tree, where the "key"
    is the entire path from the root

    Args:
        tree: A recursive dict object (a parsed yaml file)

    Returns:
        An iterator of all (path, leaf) tuples. I.e. every
        key/value in the yaml file.
    """
    
    maybe_json = lambda k,v: isinstance(v, str) and isinstance(k, str) and any((
        k.endswith(ending) for ending in ('_spec', '_ref', 'templates', 'parameters')
    ))
    
    maybe_yaml = lambda k,v: isinstance(v, str) and isinstance(k, str) and any((
        k.endswith(ending) for ending in ('manifest')
    ))
    
    for (k, v) in seq_iter(tree): 
        # Json strings
        if maybe_json(k, v):
            # This is a special case where the annotation has a json string
            try:
                branch = json.loads(v)
                if isinstance(branch, list) or isinstance(branch, dict):
                    yield from traversal(branch, parent=parent+[k])
                    continue
            except:
                pass
            
        elif maybe_yaml(k, v):
            # This is a special case where the annotation has a json string
            try:
                branch = yaml.load(v, Loader=yaml.BaseLoader)
                if isinstance(branch, list) or isinstance(branch, dict):
                    yield from traversal(branch, parent=parent+[k])
                    continue
            except:
                pass
                
        if any((isinstance(v, t) for t in (str, int, bool, float))):
            yield (parent + [k], v)
        else:
            yield from traversal(v, parent=parent+[k])



# Taken from TruffleHog
# https://raw.githubusercontent.com/feeltheajf/trufflehog3/master/truffleHog3/rules.yaml
# GPL Licensed
rules = {
    "Slack Token": "(xox[p|b|o|a]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32})"
    ,"RSA private key": "-----BEGIN RSA PRIVATE KEY-----"
    ,"SSH (DSA) private key": "-----BEGIN DSA PRIVATE KEY-----"
    ,"SSH (EC) private key": "-----BEGIN EC PRIVATE KEY-----"
    ,"PGP private key block": "-----BEGIN PGP PRIVATE KEY BLOCK-----"
    ,"Amazon AWS Access Key ID": "AKIA[0-9A-Z]{16}"
    ,"Amazon MWS Auth Token": "amzn\\.mws\\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    ,"AWS API Key": "AKIA[0-9A-Z]{16}"
    ,"Facebook Access Token": "EAACEdEose0cBA[0-9A-Za-z]+"
    ,"Facebook OAuth": '[f|F][a|A][c|C][e|E][b|B][o|O][o|O][k|K].*[''|"][0-9a-f]{32}[''|"]'
    ,"GitHub": '[g|G][i|I][t|T][h|H][u|U][b|B].*[''|"][0-9a-zA-Z]{35,40}[''|"]'
    ,"Generic API Key": '[a|A][p|P][i|I][_]?[k|K][e|E][y|Y].*[''|"][0-9a-zA-Z]{32,45}[''|"]'
    ,"Generic Secret": '[s|S][e|E][c|C][r|R][e|E][t|T].*[''|"][0-9a-zA-Z]{32,45}[''|"]'
    ,"Google API Key": "AIza[0-9A-Za-z\\-_]{35}"
    ,"Google Cloud Platform API Key": "AIza[0-9A-Za-z\\-_]{35}"
    ,"Google Cloud Platform OAuth": "[0-9]+-[0-9A-Za-z_]{32}\\.apps\\.googleusercontent\\.com"
    ,"Google Drive API Key": "AIza[0-9A-Za-z\\-_]{35}"
    ,"Google Drive OAuth": "[0-9]+-[0-9A-Za-z_]{32}\\.apps\\.googleusercontent\\.com"
    ,"Google (GCP) Service-account": '"type: "service_account"'
    ,"Google Gmail API Key": "AIza[0-9A-Za-z\\-_]{35}"
    ,"Google Gmail OAuth": "[0-9]+-[0-9A-Za-z_]{32}\\.apps\\.googleusercontent\\.com"
    ,"Google OAuth Access Token": "ya29\\.[0-9A-Za-z\\-_]+"
    ,"Google YouTube API Key": "AIza[0-9A-Za-z\\-_]{35}"
    ,"Google YouTube OAuth": "[0-9]+-[0-9A-Za-z_]{32}\\.apps\\.googleusercontent\\.com"
    ,"Heroku API Key": "[h|H][e|E][r|R][o|O][k|K][u|U].*[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}"
    ,"MailChimp API Key": "[0-9a-f]{32}-us[0-9]{1,2}"
    ,"Mailgun API Key": "key-[0-9a-zA-Z]{32}"
    ,"Password in URL": "[a-zA-Z]{3,10}://[^/\\s:@]{3,20}:[^/\\s:@]{3,20}@.{1,100}[\"'\\s]"
    ,"PayPal Braintree Access Token": "access_token\\$production\\$[0-9a-z]{16}\\$[0-9a-f]{32}"
    ,"Picatic API Key": "sk_live_[0-9a-z]{32}"
    ,"Slack Webhook": "https://hooks.slack.com/services/T[a-zA-Z0-9_]*/B[a-zA-Z0-9_]*/[a-zA-Z0-9_]*"
    ,"Stripe API Key": "sk_live_[0-9a-zA-Z]{24}"
    ,"Stripe Restricted API Key": "rk_live_[0-9a-zA-Z]{24}"
    ,"Square Access Token": "sq0atp-[0-9A-Za-z\\-_]{22}"
    ,"Square OAuth Secret": "sq0csp-[0-9A-Za-z\\-_]{43}"
    ,"Twilio API Key": "SK[0-9a-fA-F]{32}"
    ,"Twitter Access Token": "[t|T][w|W][i|I][t|T][t|T][e|E][r|R].*[1-9][0-9]+-[0-9a-zA-Z]{40}"
    ,"Twitter OAuth": '[t|T][w|W][i|I][t|T][t|T][e|E][r|R].*[''|"][0-9a-zA-Z]{35,44}[''|"]'
}

# Compile all the rules
for (k, v) in rules.items():
    rules[k] = re.compile(v)


def detect_secret(path, value, max_entropy=MAX_ENTROPY):
    """
    Args:
        path: the path leading to the key-value
        value: the actual value (bool, int, str)

    Returns:
        (int, dict) where int ∈ {0,1,2} for none,soft,hard secret.
        the dict contains a description, if there is one.
    """
    def make_jq_path(l):
        acc = ""
        for x in l:
            if isinstance(x, str):
                acc += '.' + x
            elif isinstance(x, int):
                acc += "[%d]" % x
        return acc

    human_path = make_jq_path(path)

    def mask(s):
        """
        supersecretpassword -> "***************word"
        """
        if MASK_ON:
            return "".join(
                c if i < MASK_LEN else "*"
                for (i, c) in enumerate(s[::-1])
            )[::-1]
        else:
            return s

        
    DEFAULT = (0, {
        "key": human_path,
        'value': mask(value),
    })

    # Only strings are secret
    if not isinstance(value, str):
        return DEFAULT

    # It's already escaped
    if value.startswith('{{') and value.endswith('}}'):
        return DEFAULT

    # Using an actual k8s secret (by reference)
    if 'secretKeyRef' in path:
        return DEFAULT

    # Things like env-var NAMES, and image names
    # tend to trigger the entropy checker
    for ending in SAFE_ENDINGS:
        if (not isinstance(path[-1], str)) or path[-1].lower().endswith(ending):
            return DEFAULT

    # Check the regexes - HARD violations
    for (k, regexp) in rules.items():
        if regexp.match(value):
            return 2, {
                "key": human_path,
                'value': mask(value),
                "violation": k,
            }

    # Check the entropy - SOFT violations
    h = None
    if len(value) >= 8:
        # ignore urls, urls with passwords are scanned above.
        if URL_REGEXP.match(value):
            return DEFAULT
        
        for alphabet in (HEX_CHARS, BASE64_CHARS, ASCII_CHARS):
            if set(value.upper()) <= alphabet:
                h = shannon_entropy(value, alphabet)
                if h > max_entropy:
                    return 1, {
                        "key": human_path,
                        'violation': f'Exceeded max entropy {h} > {max_entropy}',
                        'entropy': h,
                        'value': mask(value)
                    }

    # fallthrough
    return DEFAULT




def check_for_secrets(workflow) -> int:
    """
    Recurse through a workflow and scan keys for secrets.
    Apply both entropy and regexp baesd checks. (Based on TruffleHog)

    Args:
        workflow: the workflow dictionary

    Returns:
        Count of the number of potential secrets
    """
    count = 0
    # Iterate over all keys
    for (path, key) in traversal(workflow):
        (severity, desc) = detect_secret(path, key)
        if severity != 0:
            count += 1
    return count



if __name__ == '__main__':
    with open('test.yaml') as f:
        check_for_secrets(yaml.load(f, Loader=yaml.BaseLoader))
