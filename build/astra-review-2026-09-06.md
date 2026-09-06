## 1. Verdict summary

The repository does **not** enforce its advertised “validator is law” contract: schema errors are erased, fixture rendering bypasses validation, and major semantic invariant families are absent.
The v2.3 schema is substantially more expressive than v1, but the executable system remains a partial validator feeding a lossy, inference-heavy v1 adapter.
Several ordinary inputs silently change the story: allocation ranges are flattened, transfers attach to guessed splits, citations disappear, and traveller departures become fabricated survivors.
The reported test results do not establish the claimed coverage; one suite accepts crashes, and the other can report success despite missing negative fixtures.
This is a static review of the supplied files. The referenced fixture JSONs, negative-fixture files, and `AbstractStory` implementation were not supplied; their contents and reported executions cannot be independently verified here.

## 2. Logic / Ontology findings

1. **[HIGH] “Never draw a reset” is not a coherent repository-wide law.**  
   `README.md` initially treats every time-travel act as a split; `SKILL.md` explicitly allows real resets as same-lane loops; `references/method.md` says reset films are outside the tool; SPEC v2.1 onward authorizes resets and overwrites by profile. V2.2 additionally permits world collapse and dissolution. These can coexist only as **versioned, profile-scoped rules**, not simultaneous universal rules. The current documentation does not consistently make that distinction.

2. **[HIGH] Paired tines are partly structural; paired survival/death is not enforced.**  
   `schema_v2.json::$defs/split.outcomes` requires `+` and `-`, but permits empty `character_outcomes` arrays. `semantic_validate.validate_graph()` does not inspect those character outcomes or enforce:
   - distinct result universes;
   - `automatic:true` for trigger pulls;
   - a surviving traveller counterpart and a dead counterpart;
   - agreement among counterpart, character, fate, universe, and outcome event.

   A trigger split with no character outcomes can pass. In v1, a split does not even require a stub. **The central mortality claim is asserted, not enforced.**

3. **[HIGH] Split creation and arrival into an existing world are still conflated operationally.**  
   The later spec correctly separates world birth from consciousness movement. V1 joins require a source split; `v23_adapter.adapt_p1()` therefore invents that association by choosing a split in the departure universe. This cannot faithfully represent a split-independent transfer. A split birthing a world and a transfer entering an already-existing world are coherent as separate events; the adapter collapses them back into one mechanism.

4. **[HIGH] Backpropagation is neither universally appropriate nor validated where claimed.**  
   V2.3 distinguishes `initial`, `born`, `preexisting`, and witnessed `unknown` origins. However, `validate_graph()` checks only some parent/event references and ancestry cycles. It does not check:
   - birth before use;
   - unknown-origin `exists_by` witnesses;
   - immutable birth IDs or matching origin tine;
   - birth event source agreement for every born universe;
   - events after an ancestry-prefix cutoff or physical termination.

   V1 independently starts most baselines at the top regardless of proven origin. **Declared pre-existence and actual existence-before-entry are not equivalent, and the latter is unenforced.**

5. **[HIGH] “Only protagonist occupancy in a joined lane” is not enforced.**  
   Neither validator restricts events or beats to visit intervals or requires the single off-screen “elsewhen” summary. `adapt_p1()` includes events and segments from every declared universe, including unvisited worlds, without occupancy filtering. Later specifications intentionally allow unvisited negative worlds and richer world records; that is a legitimate model expansion, but it supersedes the original minimal-occupancy rule rather than implementing it.

6. **[HIGH] Non-forking travel is not reliably distinguished from branching.**  
   V1 has separate arc and join collections, but cannot establish whether their authored classification is truthful. More seriously, `adapt_p1()` turns **every transfer** into a join, irrespective of same-world travel, memory transport, signal, object custody, or observed continuity. `motions` and `gates` are not projected. The claim “non-forking travel is an arc, not a new lane” is therefore not preserved across the v2.3 pipeline.

7. **[HIGH] The authoritative thread is mostly an assertion.**  
   V1 validates token resolution but ignores `thread[]` when constructing the route. V2.3 checks some adjacent links, but permits multiple visits with zero links and ignores several link mechanisms. The adapter uses visits only for header text; the actual thread remains lane-based carry logic. Consequently, the route printed as authoritative can disagree with the route generated.

8. **[HIGH] One protagonist per chart is inconsistent with the latest contract and incompletely enforced under either interpretation.**  
   V1 has no authoritative protagonist field. V2.3 checks visit traveller equality only for the primary nonempty thread, not transfer traveller equality, complete embodiment continuity, or additional threads. R5 explicitly permits additional independently authoritative threads, contradicting the older chart prohibition. Moreover, the schema makes nonempty `additional_threads` impossible; see Architecture finding 3.

9. **[HIGH] Profile declarations are labels, not the advertised capability law.**  
   `profile()` does not expand presets. Declared parameter objects bypass virtually all capability guards. Named presets such as `tenet`, `dark`, and `looper` receive no mechanism-specific enforcement. Thus a custom `branching:"none"` document can contain multiple worlds and splits without a capability diagnostic. Conversely, legitimate P4 observed transitions are rejected. **Preset/custom equivalence and mechanism authorization are not implemented.**

10. **[HIGH] Evidence references cannot currently support production certification.**  
    `validation_profile` is unused by semantic validation. Citation sources do not resolve; `resolved` citations may have null page/scene values; production documents may contain unavailable evidence; pending evidence produces no required warning. Evidence-event arrays are generally unchecked. Even a complete validator could certify internal consistency and evidence presence—not whether an authored screenplay claim is true. The current “every lying document” rhetoric exceeds both the implementation and what these checks could establish.

## 3. Functions / Code findings

### `tools/timeline_compile.py`

1. **[HIGH — `parse_alloc()`] Documented labels and key beats parse incorrectly.**
   - `label HER: Pretty Name` stores the label under `"HER:"`, while compilation looks up `"HER"`.
   - `key: HER: 80, 90` always stores its numbers under the empty-string key because the parser extracts the text before the first colon and removes `"key"`.
   - Numeric characters in the key’s lane identifier can also enter the extracted scene list.
   - `beats: all` is accepted but never implemented.

   Ordinary documented syntax silently loses authored content.

2. **[HIGH — `parse_alloc()`, `main()`] Scene allocation is neither exact nor validated for coverage.**  
   Discontiguous ranges are stored as endpoints, then reduced to `lo = rng[0]`, `hi = rng[-1]`. An allocation such as `1-3, 20-22` can produce beats or split membership inside the unallocated gap. There are no checks for overlapping allocations, descending ranges, duplicate lanes, unknown allocation lanes, duplicate/unsorted pulls, or complete scene coverage. The compiler cannot substantiate the method’s “every scene exactly once” guarantee.

3. **[HIGH — `main()`] The compiler invents mortality and omits other required mortality.**  
   Every crossing gets a generated “HE DIES” stub without an explicit fate record. Non-crossing `split:` entries get no stub at all. Splits falling inside multiple lane envelopes can be placed multiple times. A non-crossing split outside all envelopes is defined but never placed. This contradicts both “adds NOTHING except plumbing” and the two-tine rule.

4. **[MED — `main()`] Event order and output validity have silent traps.**  
   Same-scene items are ordered by tuple-kind strings, not a declared event precedence. Numeric beat mode may duplicate split scenes; key-mode beats are not consistently restricted to occupancy before departure. `thread` always ends with `"ENDING"` even when no ending item exists. Generated JSON is never passed through the renderer validator.

5. **[MED — `parse_alloc()`, `main()`] Invalid input handling is incomplete.**  
   Unknown lines are ignored; duplicate declarations overwrite earlier data. Numeric parsing can accept malformed pull syntax by extracting digit substrings rather than validating tokens. Bad integers, canvas arguments, malformed label lines, and file errors can traceback instead of producing allocation diagnostics. Output is written directly rather than atomically.

### `tools/universe_graph.py`

6. **[HIGH — `validate()`] Arc endpoint placement is not checked against declared endpoint lanes.**  
   `arc_items` and `mark_items` retain their lane IDs, but validation only checks existence and cardinality. An arc declaring `from_lane:"A", to_lane:"B"` passes with its departure and arrival placed in the opposite lanes, provided both declared lanes exist. `build()` then follows placement, silently contradicting the arc definition.

7. **[HIGH — `validate()`] Reference existence is confused with unique, correct placement.**  
   Same-lane duplicate joins pass because the duplicate check only rejects a different lane. A defined join need not be placed at all. Split/node placements need not be unique; a join’s source split need not have a placement. Node `lane` membership is not checked. Duplicate lane and node IDs are accepted and later collapsed by dictionaries. Multiple joins may leave one split despite the nonbranching-thread requirement.

8. **[HIGH — `validate()`, `build()`] JSON object key order changes semantics.**  
   Both use `next(iter(item))` as an item discriminator. A valid-looking beat whose `cite` or `certainty` key appears first is not interpreted as a beat. Unknown item kinds are silently ignored. Empty objects cause `StopIteration`; mixed-kind objects are not rejected. JSON member ordering must not determine what story record exists.

9. **[HIGH — `build()`, CLI fixture branch] Validation is bypassable by design.**  
   `build()` never calls `validate()`. Fixture mode calls neither `semantic_validate` nor v1 `validate`; the comment calling v1 validation “advisory” is misleading because it is not called at all. `adapt()` also performs no validation. An invalid fixture can produce a successful artifact, directly contradicting the public build contract.

10. **[HIGH — `build()`, thread-vertical section] The generated route is inferred and can branch or reverse.**  
    Thread starts are inferred from absence of `laneborn`; joins resume carry; unreferenced arcs affect it; `thread[]` is unused. The downward guard applies only to some item types. A split before a lane’s first join can draw from the incoming-join coordinate backward to the split; abandon and arc branches also lack the general monotonicity check. Multiple outgoing joins generate multiple thread branches.

    Additionally, `carry_through:false` does **not** imply `arrive_thread:false`: another character’s arrival can restart the protagonist’s route unless both flags are supplied.

11. **[HIGH — `build()`, beat preparation and stub association] Authored evidence is dropped and deaths can attach to the wrong act.**  
    Flat beat `cite`, `tone`, and `side` are discarded; only the new screen/certainty/traveller siblings are preserved. Flat `chip.dim` is also discarded. The source comment explicitly preserves this loss for old output compatibility. Stubs attach to the nearest preceding split, not their declared identity; an intervening split can therefore reassign a death to the wrong act.

12. **[HIGH — `build()`, survivor census/version counters] Derived identity claims are false.**  
    The census starts every declared traveller at one survivor and adds one per arc. It ignores death, departure, current occupancy, ordinary trips, and cutoff position. A round trip creates “survivors” arithmetically. Version ordinals follow lane traversal/insertion order through `arc_pos`, not authoritative story order; beat traveller versioning is not implemented. These are semantic defects, not presentation choices.

13. **[HIGH — `build()`, arc routing; nested `elbow45()`] Connectors can lose their declared endpoints.**  
    Self-lane and cross-lane non-interval arcs finish at `(tx, ty2)` after dodging, but the arrival dot remains at `(tx, ty)`; the final attachment segment is absent. Independently, `elbow45()`’s `ady > adx` branch does not append the original target point, so some transformed paths lose their endpoint even without dodging. Both defects undermine exact-port continuity.

14. **[MED — `build()`, fixed-point restack] The eight-pass limit rejects sufficiently long valid dependency chains.**  
    With the documented right-to-left progression and left-to-right lane processing, dependencies can propagate only one lane per pass. A long acyclic chain can require more than eight iterations. Cyclic dependencies are not diagnosed separately; both conditions become `RuntimeError`, not exit-2 diagnostics. The convergence guarantee is unsupported.

15. **[MED — `validate()`, `build()`] Shape and scalar validation leaves many crash paths.**  
    Examples include non-object arcs, missing metadata required by `build()`, empty chip/segment text passed to `max()`, malformed item values, and a nonempty non-dict `meta.travellers`: validation records an error and then calls `.items()` on it. RGB values are only length-checked, and `timescale` is only truthiness-checked. Nonfinite numbers and booleans can enter numeric interval processing.

16. **[MED — `build()`, interval branch] The declared time scale is not actually used as an axis.**  
    Duration uses `abs(depart-arrive)`, fixed `PX_PER_UNIT`, and a clamp; `timescale.start` is ignored. Both forward and backward intervals first extend toward earlier schematic position. Presence of a timescale therefore does not establish the promised relationship between endpoint time and generated path.

17. **[MED — `build()`, hitbox export; `_PROTECT`/`tc()`] Output metadata and shared state are unsafe.**  
    Hitboxes are constructed as `(n,t)` but transformed as though `(t,n)`: vertical boxes are incorrectly swapped and horizontal anchors are not swapped. Text-bearing horizontal boxes also need screen-size treatment rather than a blind corner transform. This is an interaction/export-coordinate bug.

    `_PROTECT` is reset before its snapshot and remains global. Concurrent builds can corrupt each other’s protected tokens, and exceptions skip cleanup. `tc()` also changes authored text despite v2’s preservation requirement.

18. **[MED — CLI output handling] Input-derived output paths can overwrite unintended files.**  
    Default v1 output uses `graph.replace(".json", ...)`; an input without that substring becomes its own output path and is overwritten by PNG data. Fixture filenames use namespace strings with only `*` replaced: path separators and traversal components remain legal. Duplicate namespaces can overwrite each other’s artifacts.

### `build/semantic_validate.py`

19. **[HIGH — `main()`, `validate_semantics()`] All JSON Schema diagnostics are erased.**  
    `main()` appends structural errors to global `DIAG`; `validate_semantics()` immediately assigns `DIAG = []`. Schema-invalid documents can therefore exit 0. For example, a document containing only `{"interpretation_profile":"P1"}` produces schema errors that are discarded, then has no graphs to trigger semantic errors.

    This also defeats structural enforcement of forbidden merges, required fields, enums, and unknown-field rejection at the CLI boundary.

20. **[HIGH — `main()`] The validation boundary is fail-open and not robust.**  
    Missing `jsonschema` or a missing schema file skips structural validation. Standard `json.load()` accepts duplicate keys with last-write-wins semantics; malformed JSON and many wrong-shaped documents traceback. Semantic checks continue into malformed structures instead of stopping safely. Hand-written CLI argument handling misidentifies the document when options precede it and can crash on a missing `--schema` value.

21. **[HIGH — `profile()`, `validate_semantics()`, `validate_graph()`] Profile logic implements obsolete and incomplete rules.**
    - No preset expansion or parameter-combination validation.
    - `waif` with `interpretation_rules:"waif"` is rejected, despite being the specified alias.
    - `waif` with rules `"none"` is accepted.
    - P2/P3 reject all transfers, including independently authorized transport from later revisions of the spec.
    - P4 rejects legal observed transitions.
    - P2/P3 checks omit forbidden origins, split/outcome events, passes, link kinds, and required state membership.
    - P1 checks omit event/visit revision fields, revision links, and `nonexistent` fates.
    - E249 compares only universe ID sets, not world or revision declarations.
    - E247 examines loop records, not incompatible revision transition kinds.

22. **[HIGH — `validate_graph()`, thread block] A disconnected route can pass.**  
    E146 is conditional on `len(links)`, so deleting **all** links from a multi-visit thread avoids the cardinality error. Empty primary threads are accepted. Revision, gate, state-passage, and journey-gap links receive no mechanism-resolution checks. Split links do not verify destination entry ports or a surviving outcome. Visit event membership, start/final event roles, within-visit passes, transfer traveller identity, and additional threads are not validated.

23. **[HIGH — `validate_graph()`, origin/split/transfer/fate blocks] Most endpoint and lifecycle checks are absent.**  
    Existing-ID checks do not establish role or context agreement:
    - a split definition may reference a non-split event;
    - outcome entry events may belong to another universe;
    - duplicate split definitions and undefined split events are not rejected;
    - `source_disposition:"ancestry_prefix"` has no enforcement;
    - `"continues"` unnecessarily requires the `+` tine, rather than exactly one continuing source tine, and does not prevent both tines using the source;
    - transfers need not agree with endpoint event universes or event roles;
    - distinct worlds can claim `relation:"same_world"` because E112 checks only the converse case;
    - embodiment and body-transport identities are unchecked;
    - fates need not agree with their event/instance universe and may resurrect an instance.

24. **[HIGH — `validate_graph()`] Entire advertised invariant families have no implementation.**  
    Beyond the narrow checks already identified, there is no semantic validation of:
    - revision ordering, transitions, memory continuity, ladders, state selection;
    - causal-link cycles, genealogy, knots, dissolution;
    - motions, gates, pincers, body positions, bodily terminality;
    - clocks, rates, divergence systems, activations, attractors;
    - identities, object provenance, observations, presentations;
    - termination, layout membership/collapse safety, evidence manifests.

    Segments are checked only for endpoint universe membership; beats only for segment existence and a nonempty locator. Global ID uniqueness, namespace declarations/uniqueness, graph links, and most typed references are also unchecked. E251–E299 are not implemented. In particular, **E257/E258 cannot currently expose the problems attributed to them in OPEN_ISSUES.**

25. **[MED — `err()`, `index_by()`, diagnostic production] Diagnostics are unstable and shared globally.**  
    Codes have different meanings from the normative spec: for example E210/E211 are used for fate references rather than revision invariants, and E063 for ancestry cycles rather than the base origin-marking diagnostic. Array-backed paths sometimes contain entity IDs instead of array indices, so they are not valid document JSON Pointers. Results are not sorted by pointer/code.

    `DIAG` is non-reentrant shared state. `index_by()` assumes objects and hashable keys. `E()` and several collected sets/variables are unused; they do not provide the checks suggested by surrounding comments.

### `build/v23_adapter.py`

26. **[HIGH — `adapt_p1()`] Array order replaces event chronology and transfer identity.**  
    It emits all splits first, then transfers, then other events, segments, beats, and fates. `story_order`, `view_order`, visit intervals, and segment anchors are ignored. Each transfer attaches to the **last split encountered in its source universe**, not its actual exit event. Shuffling a split array changes the transfer’s meaning.

    Start/outcome events are omitted; born-lane headers can be appended after that lane’s splits. Split-following visits do not become an authoritative thread connection.

27. **[HIGH — `adapt_p1()`] The adapter invents or misstates semantic claims.**  
    Every transfer becomes a join. A missing split becomes `from_split:None`, accepted only because fixture rendering bypasses validation. Every `alive` fate becomes “alive at cutoff,” even if the fate occurred much earlier. Deaths become generic stubs and can attach to a later unrelated split. `collapsed_universes` is ignored, while all declared universes become lanes. This is not a semantics-preserving bridge.

28. **[HIGH — `adapt_single_lane()`] Valid state/observation data is discarded.**  
    It selects `universes[0]`; a multi-context P4 graph loses every other context’s events, while all beats are still appended to the selected lane regardless of segment membership. An empty universe array crashes. Revision sections precede all events rather than containing them, and iteration transitions, retained memory, fates, state passages, and termination are omitted.

    Its body-travel arc dictionaries lack v1 `from_lane`/`to_lane` fields and use unsupported `depart`/`arrive` fields. Their endpoints are appended at the end, not positioned at the referenced events.

29. **[HIGH — `_beat()`, `adapt()`] Evidence and profile disclosure are lossy.**  
    `_beat()` ignores `cite.locator`, source, and unavailable status. It looks for nonexistent status `"unresolved"` and emits invalid certainty `"unseen"` if encountered. Valid evidence-pending citations commonly become uncited beats. Beat screen/certainty/traveller fields are not forwarded.

    `adapt()` ignores root authored metadata, house rules when the preset is `"P1"`, expanded custom parameters, and the selected axis. Custom profiles get only “PARAMETRIC”; P4 connections do not get required undeclared-relation semantics. `_origin_star()` also gives unknown origins the same star used to assert pre-existence.

### `projections.py`

30. **[HIGH — `_id()`, `_world_node_id()`, `to_dot()`, `to_mermaid()`] IDs collide and namespaces merge.**  
    `_id()` retains only the first six UTF-8 bytes in hex. IDs sharing that prefix produce the same node. World node IDs omit graph namespace entirely, so identical local world IDs in separate graphs merge in DOT/Mermaid. This destroys the namespace-isolation guarantee.

31. **[MED — `to_dot()`, `to_mermaid()`, `to_markdown()`] Text serialization is not escaped; Mermaid split syntax is invalid.**  
    Quotes, newlines, brackets, backslashes, and Markdown table pipes can break output or inject additional graph structure. Mermaid split edges use `|>`/`|.` rather than valid flowchart edge syntax. `to_markdown()` calls itself cite-aware but exports no citations or evidence manifest.

    These projections expect a different normalized vocabulary—`worlds`, `route`, `profile`, flattened origins, and `source_universe`. That may be legitimate for `AbstractStory`, but its implementation and normalization contract are absent from the supplied material; direct v2.3 compatibility is not established. `render()` additionally returns `None` silently for unknown targets.

### Test suites

32. **[HIGH — `tests/test_validator.py::main()`] Crashes count as successful rejection.**  
    Negative cases pass for any nonzero exit code with no output file. Exit 1 from a traceback satisfies a suite whose stated contract is exit 2. The wrong-lane join test also creates a cross-lane duplicate, so it does not isolate wrong-lane placement. Same-lane duplicates, wrong arc placement, malformed structures, and route invariants are not tested.

33. **[MED — `tests/test_validator.py` helpers and runner] Artifact checks and positive coverage are weak.**  
    All invocations share one fixed temporary output path, causing parallel-run collisions and stale-artifact ambiguity. A negative case that exits 0 leaves its PNG for later tests. “All pass2a fields” does not exercise correct census, traveller labels, or version order—only successful rendering. Compiler parsing, adapter fidelity, schema integration, and projection semantics receive no coverage.

34. **[HIGH — `build/test_semantic.py`] Missing tests can still yield a perfect score.**  
    The runner iterates discovered JSON files, not the `EXPECTED` manifest. Missing negative fixtures are never failures, while the summary always starts from 13 expected tests. If all negative files are absent and the positive passes, it reports `13/13`.

    It also hardcodes `/tmp/fut/.venv/bin/python`; checks expected codes as substrings rather than exact diagnostic records; and tests only one positive fixture. No schema-only negative catches diagnostic erasure, no preset/custom equivalence tests exist, and no E251–E299 coverage is present. The code-line extraction can itself crash after a substring match not located at the start of a line.

## 4. Decisions / Architecture findings

1. **[HIGH] The conceptual evolution is defensible; the implementation sequence is not.**  
   V2 separates existence, embodiment, movement, and visits. V2.1 removes compulsory WAIF physics. V2.2 separates physical direction from presentation and adds mechanism capabilities. V2.3 repairs concrete identity and route ambiguities. Those are genuine modeling improvements.

   But the spec requires semantic validation before enabling the new rendering path. The implementation instead adds a permissive adapter before implementing those guarantees.

2. **[HIGH] The “frozen contract” is not the final v2.3 contract.**  
   The schema omits or cannot accommodate several R-repair requirements:
   - R7 `representation` metadata;
   - visit `activation`;
   - explicit joint state selection for multiple ladders;
   - R8 developmental linkage;
   - R9’s shown nested provenance `evidence_events`.

   Freezing a schema is useful only when its capability table, examples, validator, and compatibility policy agree. Here “frozen” freezes omissions and contradictions.

3. **[HIGH] `additionalThread` is structurally unsatisfiable.**  
   `$defs/additionalThread` combines the closed `$defs/thread` with an `allOf` branch requiring `id`. The base thread rejects `id` as an additional property. Every nonempty additional-thread record therefore fails an actual schema validation. This is an accidental contradiction, not enforcement of the old one-protagonist rule.

4. **[HIGH] The transport schema is a bag of optional fields, not a discriminated union.**  
   `$defs/transfer` universally requires `traveller` and `relation`, contradicting the complete signal and ordinary-object arms specified without those fields. Conversely, body traversal need not provide `body_transport`, and conflicting payload/embodiment fields can coexist. `$defs/endpointRef` permits an endpoint with only an unrelated endpoint key, while adapter code assumes `universe` and `entry` exist.

   The schema both rejects intended encodings and accepts incoherent ones.

5. **[HIGH] Claimed completion is materially stronger than the code.**  
   `CHANGELOG.md` claims genealogy bootstrap validation and authoritative visit-based threading; neither is implemented. `REPORT.md` describes a completed end-to-end implementation, while structural errors disappear and fixture rendering is unvalidated.

   The documented Tenet “turnstile splits” and inverted-strand lanes also contradict the normative one-world motion/gate model. Without the actual fixtures, their encoding cannot be audited, but the report’s stated interpretation is already inconsistent.

6. **[HIGH] OPEN_ISSUES is not an adequate conformance ledger.**  
   Several entries describe entirely absent checks as narrow under-checks. It also proposes a `gated-inversion` traversal arm that R1 explicitly prohibits. Divergence monotonicity and a universal 1% barrier are not generic constraints justified by the parameter model; adding them globally would introduce film-specific physics. Its claim that genealogy validates cannot be supported by `validate_graph()`.

   Honest gaps require distinguishing **unsupported**, **unchecked**, **invalid**, and **evidence pending**. These are currently blurred into successful validation.

7. **[HIGH] Ground-truth-in-data is contradicted by downstream inference and loss.**  
   Data-first architecture is undermined when compilation invents deaths, rendering invents survivor counts, adapters guess transfer anchors, and citations are intentionally discarded. Preserving incorrect legacy output is explicitly contrary to SPEC A11’s compatibility rule. “Unused by current fixtures” does not make a fabricated-count feature safe.

8. **[MED] There is no single readable normative specification or diagnostic registry.**  
   `SPEC_v23.md` contains duplicated amendments, truncated JSON, obsolete examples, retired guards still used by code, and “proposed amendments” beneath a superseding v2.3 heading. The precedence convention cannot compensate for mismatched executable definitions. Diagnostic meanings have also drifted independently of the document.

9. **[MED] The PNG prohibition is a workflow rule, not an enforced property.**  
   It is reasonable to treat PNGs as generated artifacts. Nothing supplied verifies that an artifact came from the current source or was not edited afterward. Source hashes, build manifests, and regeneration checks would enforce provenance more meaningfully than the prohibition alone. They would not, however, repair semantic mistakes in generation.

10. **[MED] V2.3 is genuinely more expressive as data, but not yet as an executable system.**  
    Explicit instances, visits, revisions, clocks, motions, causal provenance, and observations distinguish facts v1 cannot represent structurally. That is more than layering. In operation, however, many records are unchecked and then discarded into v1 lanes and beats. The current renderer cannot serve as evidence that those distinctions survived.

## 5. Risks & technical debt

1. **False certification is the immediate operational risk.**  
   Users can receive exit 0 for schema-invalid documents and successful artifacts for semantically invalid fixtures. This contaminates every downstream claim of accepted canon.

2. **Silent story corruption is harder to detect than crashes.**  
   Array-order-dependent transfer anchors, incorrect stub attachment, dropped citations, collapsed P4 contexts, and invented cutoff survival can produce plausible output that no longer represents the source.

3. **Model complexity is growing faster than enforceable semantics.**  
   Dozens of record types have no resolver or invariant coverage. Adding further presets increases the apparent support surface without increasing trustworthy behavior.

4. **Legacy compatibility is preserving known falsehoods.**  
   Keeping citation loss and survivor arithmetic for unchanged historical output makes future migration harder and encourages consumers to depend on incorrect semantics.

5. **Identity and chronology have no single normalization boundary.**  
   Compiler allocation order, event coordinates, thread visit order, lane order, and adapter insertion order compete. The same document can change meaning when unordered collections are permuted.

6. **Tests and reported coverage are unreliable release gates.**  
   Crash-accepting negatives, missing-fixture success, hardcoded interpreter paths, absent manifests, and no adapter/projection regression tests permit broad regressions behind a green summary.

7. **Future parallel/API use will expose hidden state and filesystem defects.**  
   Global diagnostics, global text-token state, shared temporary artifacts, unchecked namespace paths, and non-atomic writes are incompatible with safe concurrent builds.

## 6. Top recommendations

1. **Make validation fail closed at every public build entry point.**  
   Preserve schema diagnostics; require the structural dependency and schema; reject duplicate keys and invalid JSON with exit 2; stop semantic traversal of malformed subtrees. Route CLI, `build()`, and fixture adaptation through one shared validation API. Add the schema-error-erasure regression first.

2. **Withdraw broad v2.3 certification until capabilities are implemented.**  
   Publish a machine-readable supported-capability matrix. Reject unsupported committed mechanisms rather than accepting and silently dropping them. Separate valid syntax, semantic validation, pending evidence, and faithful projection status.

3. **Implement preset expansion and one mechanism-based validator.**  
   Normalize presets and equivalent custom profiles identically. Correct the WAIF alias, P4 observed continuity, and branch-independent transport. Remove obsolete profile-name restrictions instead of adding more exceptions.

4. **Prioritize core semantic closure before advanced film machinery.**  
   Implement typed reference resolution, uniqueness, namespace isolation, exact endpoint membership, both-tine consistency, origin/existence bounds, route cardinality, passes, mortality, and evidence completeness. Then add revisions, bodies, gates, causality, and activation families with explicit coverage.

5. **Replace the lossy adapter with an event/route-based intermediate representation.**  
   Preserve IDs, citations, context, chronology, and selected states. Construct route connections from visits and links, not lanes or nearest splits. Unsupported projections must fail explicitly or declare their omissions; they must not invent replacement mechanisms.

6. **Repair the schema before calling it frozen.**  
   Fix `additionalThread`; define real transport unions and endpoint roles; add the missing R7–R9 fields; reconcile nullability and conditional requirements. Introduce an explicit compatibility revision rather than silently accepting partial envelopes.

7. **Remove fabricated claims and repair the compiler.**  
   Disable survivor arithmetic now. Require explicit outcomes for deaths; preserve discontiguous scene sets; fix label/key/all-beat parsing; reject unknown syntax and duplicate declarations. Preserve citations and validate compiled output before writing it.

8. **Turn tests into conformance tests rather than exit-code smoke tests.**  
   Require exact exit 2 and structured codes, verify the complete fixture manifest, use isolated temporary directories and `sys.executable`, and test every shipped positive. Add mutation tests for zero links, swapped arc lanes, wrong fate context, duplicate placements, and schema-only failures. Add collection-permutation, preset/custom-equivalence, and evidence-preservation tests.

9. **Fix semantic endpoint and export defects independently of appearance.**  
   Attach routed arcs to their actual arrival ports, repair `elbow45()`, replace the fixed iteration ceiling with dependency solving and cycle diagnostics, correct hitboxes, namespace projection IDs, and escape all textual export formats.

10. **Flatten the normative docs and make artifact provenance auditable.**  
    Publish one current specification and diagnostic registry; archive amendment history separately. Update README, SKILL, method, REPORT, CHANGELOG, and OPEN_ISSUES to match demonstrated enforcement. Record source/schema/version hashes and an evidence manifest alongside generated artifacts.