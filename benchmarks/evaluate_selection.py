"""Evaluate CodeScope's test selection against real test failures.

For each mutation: inject a deliberate bug, run the real petclinic tests (ground truth),
run CodeScope on the same change, and compare. Run from the backend folder:
    python ../benchmarks/evaluate_selection.py
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

from app.engine.graph import DependencyGraph  # noqa: E402
from app.engine.impact import compute_impact  # noqa: E402
from app.engine.resolver import Resolver  # noqa: E402
from app.engine.tests_select import is_test_path, select_tests  # noqa: E402
from app.parser.scanner import scan_java_files  # noqa: E402
from app.services.git_diff import export_revision, get_changes  # noqa: E402

SRC = Path("/tmp/pc_full")
WORK = Path("/tmp/pc_eval")
CS_TMP = Path("/tmp/pc_eval_cs")
P = "src/main/java/org/springframework/samples/petclinic/"

# (label, file, exact signature text, value to return; None means void)
MUTATIONS = [
    ("Owner.getAddress -> null", P + "owner/Owner.java", "public String getAddress() {", "null"),
    ("Owner.getCity -> null", P + "owner/Owner.java", "public String getCity() {", "null"),
    ("Owner.getTelephone -> null", P + "owner/Owner.java", "public String getTelephone() {", "null"),
    ("Owner.addPet -> no-op", P + "owner/Owner.java", "public void addPet(Pet pet) {", None),
    ("Owner.getPet(String) -> null", P + "owner/Owner.java", "public Pet getPet(String name) {", "null"),
    ("Owner.getPet(Integer) -> null", P + "owner/Owner.java", "public Pet getPet(Integer id) {", "null"),
    ("Owner.addVisit -> no-op", P + "owner/Owner.java", "public void addVisit(Integer petId, Visit visit) {", None),
    ("Vet.getNrOfSpecialties -> -1", P + "vet/Vet.java", "public int getNrOfSpecialties() {", "-1"),
    ("Vet.addSpecialty -> no-op", P + "vet/Vet.java", "public void addSpecialty(Specialty specialty) {", None),
    ("NamedEntity.getName -> null", P + "model/NamedEntity.java", "public String getName() {", "null"),
    ("Pet.getBirthDate -> null", P + "owner/Pet.java", "public LocalDate getBirthDate() {", "null"),
    ("Pet.addVisit -> no-op", P + "owner/Pet.java", "public void addVisit(Visit visit) {", None),
]

MVN = [
    "./mvnw", "test",
    "-Dtest=!PostgresIntegrationTests,!MySqlIntegrationTests,!MysqlTestApplication",
    "-Dsurefire.failIfNoSpecifiedTests=false",
    "-Dspring-javaformat.skip=true", "-Dcheckstyle.skip=true", "-Dnohttp.skip=true",
]


def git(*args):
    return subprocess.run(
        ["git", "-c", "user.name=eval", "-c", "user.email=e@e", "-c", "commit.gpgsign=false",
         "-C", str(WORK), *args],
        check=True, capture_output=True, text=True).stdout.strip()


def mutate(rel, signature, value):
    path = WORK / rel
    lines = path.read_text().splitlines(keepends=True)
    hits = [i for i, l in enumerate(lines) if signature in l]
    if len(hits) != 1:
        return f"signature matched {len(hits)} lines"
    i = hits[0]
    indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())] + "  "
    stmt = "return;" if value is None else f"return {value};"
    lines.insert(i + 1, f"{indent}if (true) {{ {stmt} }}\n")
    path.write_text("".join(lines))
    return None


def run_tests():
    """Returns (failing test classes, classes run) or None if the build did not run tests."""
    reports = WORK / "target" / "surefire-reports"
    shutil.rmtree(reports, ignore_errors=True)
    subprocess.run(MVN, cwd=WORK, capture_output=True, text=True, timeout=900)
    files = list(reports.glob("TEST-*.xml"))
    if not files:
        return None
    failing, ran = set(), set()
    for f in files:
        root = ET.parse(f).getroot()
        name = root.get("name", "").split(".")[-1].split("$")[0]
        ran.add(name)
        if int(root.get("failures", 0)) + int(root.get("errors", 0)) > 0:
            failing.add(name)
    return failing, ran


def codescope(base, target):
    shutil.rmtree(CS_TMP, ignore_errors=True)
    export_revision(WORK, base, CS_TMP / "b")
    export_revision(WORK, target, CS_TMP / "t")
    bs, ts = scan_java_files(CS_TMP / "b"), scan_java_files(CS_TMP / "t")
    bg = DependencyGraph.build(bs.files, Resolver(bs.files).resolve())
    tg = DependencyGraph.build(ts.files, Resolver(ts.files).resolve())
    result = compute_impact(get_changes(WORK, base, target), ts.files, tg, bs.files, bg)
    test_files = {
        f.path: [s.qualified_name for s in f.symbols if s.kind in ("class", "interface", "enum", "record")]
        for f in ts.files if is_test_path(f.path)
    }
    return result, select_tests(result, test_files), len(test_files)


def main():
    if not WORK.exists():
        shutil.copytree(SRC, WORK, symlinks=True)
    base = git("rev-parse", "HEAD")
    rows, skipped = [], []

    for label, rel, sig, value in MUTATIONS:
        print(f"\n== {label}", flush=True)
        git("reset", "--hard", base)
        err = mutate(rel, sig, value)
        if err:
            skipped.append((label, err))
            continue
        git("commit", "-q", "-am", f"mutation: {label}")
        outcome = run_tests()
        if outcome is None:
            skipped.append((label, "build failed (no tests ran)"))
            continue
        failing, ran = outcome
        if not failing:
            skipped.append((label, "no test detects this mutation (no ground truth)"))
            continue
        result, selected, n_test_files = codescope(base, "HEAD")
        sel_all = {Path(t.path).stem for t in selected}
        sel_strong = {Path(t.path).stem for t in selected if t.confidence in ("high", "medium")}
        hit_all, hit_strong = failing & sel_all, failing & sel_strong
        rows.append({
            "label": label, "failing": failing, "missed": sorted(failing - sel_all),
            "recall_all": len(hit_all) / len(failing),
            "recall_strong": len(hit_strong) / len(failing),
            "selected": len(sel_all), "total": n_test_files,
            "changed": [c.qualified_name for c in result.changed],
            "precision": len(hit_all) / len(sel_all) if sel_all else 0.0,
        })
        r = rows[-1]
        print(f"   failing={len(failing)} selected={r['selected']}/{r['total']} "
              f"recall={r['recall_all']:.2f} missed={r['missed']}", flush=True)

    git("reset", "--hard", base)
    write_report(rows, skipped)


def write_report(rows, skipped):
    out = ["# Test selection evaluation (spring-petclinic)\n",
           "Ground truth: classes that really fail after a deliberately injected bug "
           "(`./mvnw test`, 77 baseline tests, Postgres/MySQL integration tests excluded).\n",
           "| Mutation | Failing classes | Selected / all | Recall (all) | Recall (high+medium) | Precision | Missed |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['label']} | {len(r['failing'])} | {r['selected']}/{r['total']} | "
                   f"{r['recall_all']:.2f} | {r['recall_strong']:.2f} | {r['precision']:.2f} | "
                   f"{', '.join(r['missed']) or '-'} |")
    if rows:
        n = len(rows)
        out += ["", f"**Mutations evaluated:** {n}",
                f"**Mean recall (all selected):** {sum(r['recall_all'] for r in rows) / n:.2f}",
                f"**Mean recall (high+medium only):** {sum(r['recall_strong'] for r in rows) / n:.2f}",
                f"**Mean selection size:** {sum(r['selected'] for r in rows) / n:.1f} of "
                f"{rows[0]['total']} test classes",
                f"**False negatives:** {sum(len(r['missed']) for r in rows)} test-class misses"]
    out += ["", "## Skipped"] + [f"- {l}: {why}" for l, why in skipped]
    out += ["", "## Limitations",
            "- Small, hand-picked sample of simple mutations; illustrative, not a benchmark.",
            "- Mutations that no test detects are excluded because they have no ground truth.",
            "- Recall is measured on test classes, not individual test methods.",
            "- Calls on variables of unknown type are not traced, which is the main source of misses."]
    (HERE / "results.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()