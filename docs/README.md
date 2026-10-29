# Project documentation and milestone reports

All submission documents and reports are maintained under this directory.
The repository-root README and the milestone-one component README remain entry
points for setup and execution. Data, code, weights and runtime outputs retain
their respective directories.

## Proposal and design

- [Project proposal](Project_Proposal.pdf)
- [Workflow diagram](design/Workflow.png) and [editable diagram](design/Workflow.drawio)

## Milestone 1

- [Data evidence and feasibility review](milestone1/DATA_EVIDENCE.md)
- Original sample data and generated feasibility images remain in
  `milestone1/posture_check/`; they are inputs/runtime artifacts rather than reports.

## Milestone 2

- [Progress report and task designation](MILESTONE2_STATUS.md)
- [Hand-in checklist](MILESTONE2_HANDIN.md)
- [Current data card](MILESTONE2_DATA_CARD.md)
- [Dataset preparation](DATASET_PREPARATION_M2.md) and [acquisition evidence](DATA_ACQUISITION.md)
- Original cards: [Mendeley](data_cards/DATA_CARD_MENDELEY.md), [REHAB24](data_cards/DATA_CARD_REHAB24.md)
- [Validation protocol](VALIDATION_PROTOCOL.md), [measured results](results/),
  and [six sample outputs](evidence/milestone2/README.md)

## Milestone 3

- [Editable testing report](phase3/Phase3_Testing_Report.docx)
- [Comparison CSV](phase3/comparison_summary.csv)
- [Reference metrics and confusion matrices](phase3/reference_metrics.json)
- [User-supplied reference annotations](phase3/reference_annotations.json)
- [Fixed test manifest](phase3/test_manifest.json) and [original test log](phase3/test_log.json)
- [Failure manifest](phase3/failure_manifest.json) and [failure contact sheet](phase3/failure_contact_sheet.jpg)

Historical logs preserve paths used during their original runs, including the
former `reports/phase3/` location. Current files and new generator outputs use
`docs/phase3/`. No inference results were changed by this reorganization.

Generated download ZIPs are stored locally in `docs/` and excluded from Git;
the underlying report, scripts, metrics and evidence are versioned here.
