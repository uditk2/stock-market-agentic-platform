# W14 Pipeline Storage Tasks (Iteration 3)

1. Diagnose (completed): failure is quota exhaustion at artifact upload.
2. Track work item: issue draft + repository issue.
3. Recovery: free storage now by pruning historical `Build Installers` runs beyond latest 3.
4. Prevention: add scheduled cleanup workflow (daily UTC) retaining only latest 3 runs.
5. Verification: confirm workflow file validity and successful dispatch capability.
6. Delivery: commit/push, close issue, and send Telegram completion with residual risk notes.
