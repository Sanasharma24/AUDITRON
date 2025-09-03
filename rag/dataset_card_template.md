---
tags:
- auditron
- synthetic

task_categories:
- text-generation
- text2text-generation
---

# Dataset Card for {repo_id}
This dataset was created using the [auditron](https://github.com/auditron-AI/auditron) library, an open-source Python framework designed to evaluate and test AI systems. auditron helps identify performance, bias, and security issues in AI applications, supporting both LLM-based systems like RAG agents and traditional machine learning models for tabular data.

This dataset is a QA (Question/Answer) dataset, containing {num_items} pairs.

## Usage

You can load this dataset using the following code:

```python
from auditron.rag.testset import QATestset
test_set = QATestset.load_from_hub("{repo_id}")
```

Refer to the following tutorial to use it for evaluating your RAG engine: [RAG evaluation tutorial](https://docs.auditron.ai/en/stable/open_source/testset_generation/rag_evaluation/index.html).

## Configuration

The configuration relative to the dataset generation:

```bash
{config}
```

---

<h2 style="text-align: center;">
  <span style="display: inline-flex; align-items: center; gap: 8px;">
    Built with 
    <a href="https://auditron.ai" target="_blank" style="display: inline-flex;">
      <img src="https://cdn.prod.website-files.com/601d6f7d0b9c984f07bf10bc/62983fa8ef716259c397a57d_logo.svg" 
             alt="auditron Logo" 
             width="100">
    </a>
  </span>
</h2>