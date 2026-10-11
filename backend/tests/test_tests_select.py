from app.engine.changes import FileChange
from app.engine.impact import AffectedSymbol, ChangedSymbol, ImpactResult, Uncertainty
from app.engine.tests_select import compute_risk, select_tests, top_class

MAIN = "src/main/java/app/Owner.java"
T1 = "src/test/java/app/OwnerTests.java"
T2 = "src/test/java/app/ServiceTests.java"
T3 = "src/test/java/other/UnrelatedTests.java"


def make_result(**kw):
    changed = [ChangedSymbol("app.Owner.save()", "method", MAIN, "modified")]
    affected = [
        AffectedSymbol("app.ServiceTests.run()", "method", T2, 2, True, "app.Owner.save()",
                       ("app.ServiceTests.run()", "app.Service.go()", "app.Owner.save()")),
        AffectedSymbol("app.Service.go()", "method", "src/main/java/app/Service.java", 1, True,
                       "app.Owner.save()", ("app.Service.go()", "app.Owner.save()")),
    ]
    return ImpactResult(changes=[FileChange(MAIN, "modified")], changed=changed,
                        affected=kw.get("affected", affected),
                        uncertainties=kw.get("uncertainties", []))


FILES = {T1: ["app.OwnerTests"], T2: ["app.ServiceTests"], T3: ["other.UnrelatedTests"]}


def test_top_class():
    assert top_class("app.Owner.save(int)") == "app.Owner"
    assert top_class("app.Owner.Inner.f()") == "app.Owner"


def test_selection_and_reasons():
    sel = select_tests(make_result(), FILES)
    by = {c.path: c for c in sel}
    assert set(by) == {T1, T2}                 # unrelated test is not selected
    assert any("name matches" in r for r in by[T1].reasons)
    assert any("reaches changed code 2 step" in r for r in by[T2].reasons)
    assert all(c.score > 0 and c.reasons for c in sel)
    assert [c.path for c in sel] == sorted([c.path for c in sel], key=lambda p: (-by[p].score, p))


def test_uncertain_path_scores_lower():
    sure = select_tests(make_result(), FILES)
    aff = [AffectedSymbol("app.ServiceTests.run()", "method", T2, 2, False, "app.Owner.save()",
                          ("app.ServiceTests.run()", "app.Service.go()", "app.Owner.save()"))]
    unsure = select_tests(make_result(affected=aff), FILES)
    s = {c.path: c.score for c in sure}[T2]
    u = {c.path: c.score for c in unsure}[T2]
    assert u < s


def test_risk_is_explainable_and_bounded():
    result = make_result()
    risk = compute_risk(result, select_tests(result, FILES), 100, {"app.Owner.save()": 3})
    assert 0 <= risk.total <= 100
    assert risk.total == round(sum(f.points for f in risk.factors), 1)
    assert all(0 <= f.points <= f.max_points for f in risk.factors)
    assert risk.level in {"low", "medium", "high", "critical"}


def test_risk_grows_with_blast_radius_and_gaps():
    small = make_result(affected=[])
    big_aff = [AffectedSymbol(f"app.X{i}.f()", "method", "src/main/java/app/X.java", 1 + i % 4,
                              True, "app.Owner.save()", ()) for i in range(40)]
    big = make_result(affected=big_aff, uncertainties=[Uncertainty(MAIN, "x")] * 5)
    r_small = compute_risk(small, [], 100)
    r_big = compute_risk(big, [], 100, {"app.Owner.save()": 20})
    assert r_big.total > r_small.total
    gap = next(f for f in r_big.factors if f.name == "Test gap")
    assert gap.points == 10.0                  # no test reaches the changed symbol
