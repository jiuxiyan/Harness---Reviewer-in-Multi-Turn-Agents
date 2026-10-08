# Sources and redistribution boundaries

This document preserves the public source locations and rights cautions needed to understand the historical analyses. It records the position documented on 7 October 2026; licenses and remote availability were not rechecked for this synthesis. Public access alone is not permission to redistribute a file. A license for a code repository does not automatically license separately hosted traces, derived vectors, or copied task text.

## Public outcome metadata

The fixed-setup and constructed decision-validity audits used these two input files from the public swe-agent-subset-selection vector release. They are dependencies for reproduction and are intentionally not included here.

### Vector filename manifest

- File: `single_setup_vectors.md5`
- Recorded size: 7,162,602 bytes
- [Recorded versioned source page](https://huggingface.co/datasets/Mahmoud-queens/swe-agent-subset-selection-vectors/blob/fc4b2eb330408d8c1c431817a5566a736272ccc6/single_setup_vectors.md5)
- Recorded SHA256: `d4c03560181ed4f024bcf607150808eb7ff7a8dd687d332c3fe0ef67ace755d4`

### Trajectory mapping

- File: `single_setup_repository_map.json`
- Recorded size: 3,962,675 bytes
- [Recorded versioned source page](https://huggingface.co/datasets/Mahmoud-queens/swe-agent-subset-selection-vectors/blob/1f6b64d67f1eedd4806f48633a2220e9d890373b/single_setup_repository_map.json)
- Recorded SHA256: `65b5aaf7b258dff691b3e012cb98a78e8cec5a79be38db1798571bc027fa91f8`

The combined input size was 11,125,277 bytes. Both retrieved files matched the publisher's recorded MD5 values; SHA256 values were independently computed for stable byte identification. These checks authenticate the analyzed file bytes, not original model configuration, sampling independence, or downstream rights.

Relevant provenance:

- [Original Nebius trajectory dataset](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories), with source dataset revision recorded as `35455389ab51bf5e2306bfd436ef72d0f98bf882` by the replication repository.
- [Original collection description](https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b), supporting the reported setup and filtering/collection limitations.
- [Versioned grouping implementation](https://github.com/SAILResearch/swe-agent-subset-selection/blob/daed756c5d10aafbc9e4c9b7cbef8d080be43721/pipeline/group_runs.py), supporting the per-task file-order interpretation.
- [Related paper consulted for the data setting](https://arxiv.org/html/2609.24928v1).
- [Replication repository license file](https://github.com/SAILResearch/swe-agent-subset-selection/blob/main/LICENSE), recorded as a placeholder in the historical audit.

The original Nebius dataset declared CC BY 4.0. That declaration should not be silently extended to every file in the separate replication/vector release, whose separate grant was unclear. Preserve source attribution and terms when acquiring inputs. Raw maps, manifests, selected identifiers, traces, embeddings, and upstream-authored code are excluded from this public history. A new project's code license must not purport to relicense those materials.

## Natural trajectory evidence

The natural-evidence audit used the [SWE-bench experiments repository](https://github.com/SWE-bench/experiments) and one [versioned 2024-era SWE-agent/GPT-4 Lite submission](https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/lite/20240402_sweagent_gpt4). The separately hosted [object listing](https://swe-bench-submissions.s3.amazonaws.com/?list-type=2&prefix=lite%2F20240402_sweagent_gpt4%2F&max-keys=1000) was recorded as containing 300 trajectories, 284 evaluation logs, and one predictions file. These are collection-inventory counts, not the 20-task sample counts.

The historical audit recorded per-object hashes, but the repository commit alone cannot identify immutable hosted bytes. It also could not establish all agent/evaluator/environment versions or exact evaluated-patch equality.

The inspected current [SWE-agent code license](https://raw.githubusercontent.com/SWE-agent/SWE-agent/main/LICENSE) and [SWE-bench code license](https://raw.githubusercontent.com/SWE-bench/SWE-bench/main/LICENSE) were MIT. No explicit license covering the separately hosted trajectory/log artifacts was verified from the submission's metadata, README, or experiments root. The release therefore uses a synthesized aggregate decision record and links to the original collection, without raw trace text, patches, selected task lists, or annotation dumps.

## Authored synthetic branches

The contract-evidence and change-replay branches describe their worlds, controls, fixtures, and tapes as independently authored synthetic material. They do not need a third-party dataset to run. Their source/result files may be release candidates subject to the project's chosen license and final content review; this history does not independently grant rights or choose a license for the repository.

Synthetic identifiers and expected values are test fixtures. They must remain clearly labeled as authored, and evaluator-only labels must remain separate from policy inputs. Historical test passes establish bounded implementation properties, not model performance.

## Literature citations

[Current proposal and related work](CURRENT_PROPOSAL.md) links the versioned primary papers used to narrow the claim. It paraphrases their relevance and limitations rather than republishing their text or figures. The original audit inspected relevant sections but did not reproduce the papers' experiments. Preprint status is sufficient for these citations; conference acceptance is not inferred from a manuscript template or an unverified secondary index.

The preliminary contract branch listed additional research leads that it had not fetched. Those leads are not treated here as verified literature findings. Similarly, standard exact testing and Holm correction in the decision audit do not create a new statistical contribution.

## Release rule

Keep independently authored implementation, explicitly labeled synthetic fixtures, audited aggregate results, and this synthesized decision record distinct from third-party source artifacts. Preserve source/license notices for any material that is later approved for inclusion. If byte-preserving reproduction conflicts with a necessary public-data removal or wording change, publish a clearly identified derivative and document the changed hashes rather than presenting it as the original frozen artifact.
