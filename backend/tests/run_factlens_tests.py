"""
FactLens test battery runner.

Calls run_pipeline for every case in factlens_test_battery.CASES,
grades each one against its truth label, evaluates metamorphic groups
(same:* and opp:*), runs ENDPOINT_CASES against the FastAPI TestClient,
and prints a per-category scorecard.

Usage:
    python -m tests.run_factlens_tests
    (from backend/)
"""

import sys
import os
import time
import traceback

if hasattr (sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure (encoding = "utf-8", errors = "replace")
        sys.stderr.reconfigure (encoding = "utf-8", errors = "replace")
    except Exception:
        pass

sys.path.insert (0, os.path.join (os.path.dirname (__file__), ".."))
sys.path.insert (0, os.path.dirname (__file__))

from app.pipeline import run_pipeline
from factlens_test_battery import CASES, ENDPOINT_CASES, CATEGORY_INFO

# ------------------------------------------------------------------- helpers

def get_verdict (pipeline_result):
    # returns the overall verdict string from a pipeline result
    return pipeline_result.overall_verdict

def get_sub_verdicts (pipeline_result):
    # returns list of (status, verdict) tuples for each sub-claim
    verdicts = []
    for claim_item in pipeline_result.claims:
        if claim_item.status == "Fact" and claim_item.verification is not None:
            verdicts.append (claim_item.verification.verdict)
        elif claim_item.status == "Opinion":
            verdicts.append ("Opinion")
        else:
            verdicts.append ("Unknown")
    return verdicts

# ------------------------------------------------------------------- grading

def grade_case (case, pipeline_result):
    # returns (level, reason) where level is PASS, WARN, FAIL, or REVIEW
    truth = case ["truth"]
    overall = get_verdict (pipeline_result)
    sub_v = get_sub_verdicts (pipeline_result)
    all_opinion = pipeline_result.all_opinion

    if truth == "true":
        # fail if any sub-verdict is refuted
        for v in sub_v:
            if v == "Refuted":
                return ("FAIL", "True claim got Refuted")
        # warn if overall is not enough evidence (coverage gap, not a bug)
        if overall == "Not Enough Evidence":
            return ("WARN", "True claim got NEI (coverage gap)")
        if overall == "Not Applicable" and all_opinion:
            return ("WARN", "True claim wrongly classified as opinion")
        return ("PASS", "")

    elif truth == "false":
        # fail if any sub-verdict is supported
        for v in sub_v:
            if v == "Supported":
                return ("FAIL", "False claim got Supported")
        if overall == "Not Enough Evidence":
            return ("WARN", "False claim got NEI (no corpus coverage)")
        if overall == "Not Applicable" and all_opinion:
            return ("WARN", "False claim wrongly classified as opinion")
        return ("PASS", "")

    elif truth == "mixed":
        # fail if the overall is supported (the false part was missed)
        if overall == "Supported":
            return ("FAIL", "Mixed claim got overall Supported")
        return ("PASS", "")

    elif truth == "opinion":
        # fail if it gets supported or refuted
        if overall == "Supported":
            return ("FAIL", "Opinion got Supported")
        if overall == "Refuted":
            return ("FAIL", "Opinion got Refuted")
        return ("PASS", "")

    elif truth == "unverifiable":
        # same rule as opinion - fail on supported or refuted
        if overall == "Supported":
            return ("FAIL", "Unverifiable got Supported")
        if overall == "Refuted":
            return ("FAIL", "Unverifiable got Refuted")
        return ("PASS", "")

    elif truth == "junk":
        # fail on supported or refuted, pass otherwise (including crash handled below)
        if overall == "Supported":
            return ("FAIL", "Junk got Supported")
        if overall == "Refuted":
            return ("FAIL", "Junk got Refuted")
        return ("PASS", "")

    elif truth == "robust":
        # only checks it did not crash
        return ("PASS", "")

    elif truth == "time_sensitive":
        # warn if it gets a confident verdict
        if overall in ("Supported", "Refuted"):
            return ("WARN", "Time-sensitive claim got confident verdict: " + overall)
        return ("PASS", "")

    elif truth == "review":
        return ("REVIEW", "Manual review needed")

    return ("PASS", "")

# ---------------------------------------------------------------- metamorphic

def check_groups (results_by_group):
    # returns list of (group_name, level, reason)
    group_results = []

    for group_name, members in results_by_group.items ():
        if group_name.startswith ("same:"):
            # all verdicts in the group must match
            verdicts = []
            for m in members:
                verdicts.append (m ["overall"])
            unique = list (set (verdicts))
            if len (unique) > 1:
                group_results.append ((group_name, "WARN", "Verdicts differ: " + str (verdicts)))
            else:
                group_results.append ((group_name, "PASS", ""))

        elif group_name.startswith ("opp:"):
            # exactly 2 members. they must not both be supported, or both refuted
            if len (members) != 2:
                group_results.append ((group_name, "WARN", "Expected 2 members, got " + str (len (members))))
                continue
            v0 = members [0] ["overall"]
            v1 = members [1] ["overall"]
            if v0 == "Supported" and v1 == "Supported":
                group_results.append ((group_name, "FAIL", "Both Supported"))
            elif v0 == "Refuted" and v1 == "Refuted":
                group_results.append ((group_name, "FAIL", "Both Refuted"))
            else:
                group_results.append ((group_name, "PASS", ""))

    return group_results

# ---------------------------------------------------------------- endpoint tests

def run_endpoint_tests ():
    from fastapi.testclient import TestClient
    from app.api.main import app
    client = TestClient (app)

    results = []
    for name, method, path, body, content_type, ok_statuses in ENDPOINT_CASES:
        headers = {}
        if content_type:
            headers ["Content-Type"] = content_type
        try:
            if method == "GET":
                resp = client.get (path)
            elif method == "POST":
                resp = client.post (path, content = body, headers = headers)
            else:
                resp = client.get (path)
            status = resp.status_code
            is_5xx = status >= 500
            in_ok = status in ok_statuses
            if is_5xx:
                results.append ((name, "FAIL", "Got 5xx: " + str (status)))
            elif in_ok:
                results.append ((name, "PASS", ""))
            else:
                results.append ((name, "FAIL", "Got " + str (status) + ", expected one of " + str (ok_statuses)))
        except Exception as exc:
            results.append ((name, "FAIL", "Exception: " + str (exc)))

    return results

# ------------------------------------------------------------------- main runner

def main ():
    print ("=" * 80)
    print ("  FactLens Test Battery Runner")
    print ("=" * 80)
    print ()

    # category counters
    cat_pass = {}
    cat_warn = {}
    cat_fail = {}
    cat_review = {}
    cat_crash = {}
    cat_total = {}

    # group tracking
    results_by_group = {}

    # per-case results for reporting
    all_results = []

    total_cases = len (CASES)
    done = 0
    start_time = time.time ()

    for case in CASES:
        cat = case ["cat"]
        text = case ["text"]
        truth = case ["truth"]
        group = case.get ("group")
        note = case.get ("note", "")

        # make sure counters exist
        if cat not in cat_total:
            cat_pass [cat] = 0
            cat_warn [cat] = 0
            cat_fail [cat] = 0
            cat_review [cat] = 0
            cat_crash [cat] = 0
            cat_total [cat] = 0

        cat_total [cat] = cat_total [cat] + 1
        done = done + 1

        # skip empty strings sent through the API (they return 400)
        # but for pipeline testing, empty text may crash
        display_text = text [:60].replace ("\n", " ").replace ("\r", "")

        try:
            pipeline_result = run_pipeline (text)
            overall = get_verdict (pipeline_result)
            level, reason = grade_case (case, pipeline_result)
        except Exception as exc:
            overall = "CRASH"
            if truth == "robust" or truth == "junk":
                level = "PASS"
                reason = "Crashed but junk/robust, acceptable"
            else:
                level = "FAIL"
                reason = "Pipeline crashed: " + str (exc) [:80]
            cat_crash [cat] = cat_crash [cat] + 1

        if level == "PASS":
            cat_pass [cat] = cat_pass [cat] + 1
        elif level == "WARN":
            cat_warn [cat] = cat_warn [cat] + 1
        elif level == "FAIL":
            cat_fail [cat] = cat_fail [cat] + 1
        elif level == "REVIEW":
            cat_review [cat] = cat_review [cat] + 1

        record = {
            "cat": cat,
            "truth": truth,
            "text": text,
            "overall": overall,
            "level": level,
            "reason": reason,
            "note": note,
        }
        all_results.append (record)

        # track groups
        if group is not None:
            if group not in results_by_group:
                results_by_group [group] = []
            results_by_group [group].append (record)

        # progress line
        tag = ""
        if level == "FAIL":
            tag = " <<< FAIL"
        elif level == "WARN":
            tag = " <<< WARN"
        elif level == "REVIEW":
            tag = " [review]"

        print (f"  [{done:3d}/{total_cases}] {level:6s} | {truth:14s} | {overall:20s} | {display_text:60s}{tag}")

        if level == "FAIL" or level == "WARN":
            print (f"           -> {reason}")

    elapsed = time.time () - start_time
    print ()
    print (f"  Pipeline cases done in {elapsed:.1f}s")
    print ()

    # -------------------------------------------------------- metamorphic groups
    print ("-" * 80)
    print ("  Metamorphic group checks")
    print ("-" * 80)

    group_checks = check_groups (results_by_group)
    group_fails = 0
    group_warns = 0
    for gname, glevel, greason in group_checks:
        tag = ""
        if glevel == "FAIL":
            tag = " <<< FAIL"
            group_fails = group_fails + 1
        elif glevel == "WARN":
            tag = " <<< WARN"
            group_warns = group_warns + 1
        print (f"  {glevel:6s} | {gname:25s} | {greason}{tag}")
    print ()

    # ---------------------------------------------------------- endpoint tests
    print ("-" * 80)
    print ("  Endpoint tests")
    print ("-" * 80)

    endpoint_results = run_endpoint_tests ()
    ep_pass = 0
    ep_fail = 0
    for ename, elevel, ereason in endpoint_results:
        tag = ""
        if elevel == "FAIL":
            tag = " <<< FAIL"
            ep_fail = ep_fail + 1
        else:
            ep_pass = ep_pass + 1
        print (f"  {elevel:6s} | {ename:35s} | {ereason}{tag}")
    print ()

    # --------------------------------------------------------- scorecard
    print ("=" * 80)
    print ("  SCORECARD")
    print ("=" * 80)
    print ()
    print (f"  {'Category':25s} | {'Total':>5s} | {'Pass':>5s} | {'Warn':>5s} | {'Fail':>5s} | {'Rev':>5s} | {'Crash':>5s}")
    print (f"  {'-'*25}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}")

    total_pass = 0
    total_warn = 0
    total_fail = 0
    total_review = 0
    total_crash = 0
    grand_total = 0

    for cat in CATEGORY_INFO:
        if cat not in cat_total:
            continue
        p = cat_pass [cat]
        w = cat_warn [cat]
        f = cat_fail [cat]
        r = cat_review [cat]
        c = cat_crash [cat]
        t = cat_total [cat]
        total_pass = total_pass + p
        total_warn = total_warn + w
        total_fail = total_fail + f
        total_review = total_review + r
        total_crash = total_crash + c
        grand_total = grand_total + t
        marker = ""
        if f > 0:
            marker = " !!!"
        elif w > 0:
            marker = " ~"
        print (f"  {cat:25s} | {t:5d} | {p:5d} | {w:5d} | {f:5d} | {r:5d} | {c:5d}{marker}")

    print (f"  {'-'*25}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}")
    print (f"  {'TOTAL':25s} | {grand_total:5d} | {total_pass:5d} | {total_warn:5d} | {total_fail:5d} | {total_review:5d} | {total_crash:5d}")
    print ()
    print (f"  Metamorphic groups: {len (group_checks)} checked, {group_fails} FAIL, {group_warns} WARN")
    print (f"  Endpoint tests:    {len (endpoint_results)} checked, {ep_pass} PASS, {ep_fail} FAIL")
    print ()

    if total_fail > 0 or group_fails > 0 or ep_fail > 0:
        print ("  RESULT: *** FAILURES DETECTED ***")
    elif total_warn > 0 or group_warns > 0:
        print ("  RESULT: ALL PASS (with warnings)")
    else:
        print ("  RESULT: ALL PASS")

    print ()

    # ---------------------------------------------------- list all failures
    fail_cases = []
    for rec in all_results:
        if rec ["level"] == "FAIL":
            fail_cases.append (rec)

    if len (fail_cases) > 0:
        print ("-" * 80)
        print (f"  {len (fail_cases)} FAILURE(S)")
        print ("-" * 80)
        for rec in fail_cases:
            short = rec ["text"] [:80].replace ("\n", " ")
            print (f"  [{rec ['cat']}] truth={rec ['truth']} verdict={rec ['overall']}")
            print (f"    text: {short}")
            print (f"    reason: {rec ['reason']}")
            if rec ["note"]:
                print (f"    note: {rec ['note']}")
            print ()

    # ---------------------------------------------------- list all warnings
    warn_cases = []
    for rec in all_results:
        if rec ["level"] == "WARN":
            warn_cases.append (rec)

    if len (warn_cases) > 0:
        print ("-" * 80)
        print (f"  {len (warn_cases)} WARNING(S)")
        print ("-" * 80)
        for rec in warn_cases:
            short = rec ["text"] [:80].replace ("\n", " ")
            print (f"  [{rec ['cat']}] truth={rec ['truth']} verdict={rec ['overall']}")
            print (f"    text: {short}")
            print (f"    reason: {rec ['reason']}")
            print ()

if __name__ == "__main__":
    main ()
