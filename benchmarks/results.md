# Test selection evaluation (spring-petclinic)

Ground truth: classes that really fail after a deliberately injected bug (`./mvnw test`, 77 baseline tests, Postgres/MySQL integration tests excluded).

| Mutation | Failing classes | Selected / all | Recall (all) | Recall (high+medium) | Precision | Missed |
|---|---|---|---|---|---|---|
| Owner.getAddress -> null | 1 | 6/20 | 1.00 | 0.00 | 0.17 | - |
| Owner.getCity -> null | 1 | 6/20 | 1.00 | 0.00 | 0.17 | - |
| Owner.getTelephone -> null | 1 | 6/20 | 1.00 | 0.00 | 0.17 | - |
| Owner.addPet -> no-op | 6 | 7/20 | 0.83 | 0.83 | 0.71 | PetClinicConcurrencyTests |
| Owner.getPet(String) -> null | 2 | 8/20 | 1.00 | 1.00 | 0.25 | - |
| Owner.getPet(Integer) -> null | 3 | 8/20 | 1.00 | 0.33 | 0.38 | - |
| Owner.addVisit -> no-op | 1 | 7/20 | 1.00 | 1.00 | 0.14 | - |
| Vet.getNrOfSpecialties -> -1 | 1 | 3/20 | 1.00 | 1.00 | 0.33 | - |
| NamedEntity.getName -> null | 6 | 6/20 | 0.83 | 0.83 | 0.83 | PetControllerTests |
| Pet.getBirthDate -> null | 3 | 6/20 | 0.67 | 0.33 | 0.33 | PetClinicConcurrencyTests |
| Pet.addVisit -> no-op | 1 | 7/20 | 1.00 | 1.00 | 0.14 | - |

**Mutations evaluated:** 11
**Mean recall (all selected):** 0.94
**Mean recall (high+medium only):** 0.58
**Mean selection size:** 6.4 of 20 test classes
**False negatives:** 3 test-class misses

## Skipped
- Vet.addSpecialty -> no-op: no test detects this mutation (no ground truth)

## Limitations
- Small, hand-picked sample of simple mutations; illustrative, not a benchmark.
- Mutations that no test detects are excluded because they have no ground truth.
- Recall is measured on test classes, not individual test methods.
- Calls on variables of unknown type are not traced, which is the main source of misses.
