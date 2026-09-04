# W15 Quota Remediation Tasks (Iteration 2)

1. Verify failing uploads still map to quota error signature.
2. Open one focused remediation issue.
3. Execute artifact purge first (highest immediate storage reclaim).
4. Execute run-history prune second (cross-workflow, keep latest 3).
5. Trigger `Build Installers` on current `master` and observe upload steps.
6. Compare with earlier successful run window and provide explanation.
7. Report and close tracking item.
