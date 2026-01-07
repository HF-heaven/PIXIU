import collections
import itertools
import numpy as np
import random

from lm_eval.utils import positional_deprecated, run_task_tests
import lm_eval.metrics
import lm_eval.models
import lm_eval.tasks
import lm_eval.base

from model_prompt import MODEL_PROMPT_MAP
from chatlm import ChatLM
import tasks as ta
from codexlm import CodexLM

@positional_deprecated
def simple_evaluate(
    model,
    model_args=None,
    tasks=[],
    num_fewshot=0,
    batch_size=None,
    max_batch_size=None,
    device=None,
    no_cache=False,
    limit=None,
    bootstrap_iters=100,
    description_dict=None,
    check_integrity=False,
    decontamination_ngrams_path=None,
    write_out=False,
    output_base_path=None,
    model_prompt=None
):
    """Instantiate and evaluate a model on a list of tasks.

    :param model: Union[str, LM]
        Name of model or LM object, see lm_eval.models.get_model
    :param model_args: Optional[str]
        String arguments for each model class, see LM.create_from_arg_string.
        Ignored if `model` argument is a LM object.
    :param tasks: list[Union[str, Task]]
        List of task names or Task objects. Task objects will be taken to have name task.EVAL_HARNESS_NAME if defined and type(task).__name__ otherwise.
    :param num_fewshot: int
        Number of examples in few-shot context
    :param batch_size: int or str, optional
        Batch size for model
    :param max_batch_size: int, optional
        Maximal batch size to try with automatic batch size detection
    :param device: str, optional
        PyTorch device (e.g. "cpu" or "cuda:0") for running models
    :param no_cache: bool
        Whether or not to cache
    :param limit: int or float, optional
        Limit the number of examples per task (only use this for testing), If <1, limit is a percentage of the total number of examples.
    :param bootstrap_iters:
        Number of iterations for bootstrap statistics
    :param description_dict: dict[str, str]
        Dictionary of custom task descriptions of the form: `task_name: description`
    :param check_integrity: bool
        Whether to run the relevant part of the test suite for the tasks
    :param write_out: bool
        If True, write details about prompts and logits to json for all tasks
    :param output_base_path: str, optional
        Directory to which detailed eval info will be written. Defaults to present working dir.
    :return
        Dictionary of results
    """
    random.seed(1234)
    np.random.seed(1234)

    assert len(tasks) != 0, "No tasks specified"

    if isinstance(model, str):
        if model_args is None:
            model_args = ""
        if model == "codex":
            # Parse model_args to get the actual model name and harbor_mode
            args_dict = {}
            if model_args:
                for arg in model_args.split(","):
                    if "=" in arg:
                        k, v = arg.split("=", 1)
                        args_dict[k.strip()] = v.strip()
                    else:
                        # Handle boolean flags like "harbor_mode"
                        if arg.strip() == "harbor_mode":
                            args_dict["harbor_mode"] = True
            codex_model = args_dict.get("model", "gpt-5-mini")
            harbor_mode = args_dict.get("harbor_mode", False)
            if isinstance(harbor_mode, str):
                harbor_mode = harbor_mode.lower() in ("true", "1", "yes")
            lm = CodexLM(model=codex_model, harbor_mode=harbor_mode)
        elif model[:3] != "gpt":
            lm = lm_eval.models.get_model(model).create_from_arg_string(
                model_args, {"batch_size": batch_size, "max_batch_size": max_batch_size, "device": device}
            )
        else:
            lm = ChatLM(model)
    else:
        assert isinstance(model, lm_eval.base.LM)
        lm = model

    if not no_cache:
        lm = lm_eval.base.CachingLM(
            lm,
            "lm_cache/"
            + (model if isinstance(model, str) else model.model.config._name_or_path)
            + "_"
            + model_args.replace("=", "-").replace(",", "_").replace("/", "-")
            + ".db",
        )

    task_dict = ta.get_task_dict(tasks)

    if check_integrity:
        run_task_tests(task_list=tasks)

    results = evaluate(
        lm=lm,
        task_dict=task_dict,
        num_fewshot=num_fewshot,
        limit=limit,
        bootstrap_iters=bootstrap_iters,
        description_dict=description_dict,
        decontamination_ngrams_path=decontamination_ngrams_path,
        write_out=write_out,
        output_base_path=output_base_path,
        model_prompt=model_prompt
    )

    # add info about the model and few shot config
    results["config"] = {
        "model": (model if isinstance(model, str) else model.model.config._name_or_path),
        "model_args": model_args,
        "num_fewshot": num_fewshot,
        "batch_size": batch_size,
        "batch_sizes": list(lm.batch_sizes.values()) if hasattr(lm, "batch_sizes") else [],
        "device": device,
        "no_cache": no_cache,
        "limit": limit,
        "bootstrap_iters": bootstrap_iters,
        "description_dict": description_dict,
    }

    return results


decontaminate_suffix = "_decontaminate"


@positional_deprecated
def evaluate(
    lm,
    task_dict,
    provide_description=None,
    num_fewshot=0,
    limit=None,
    bootstrap_iters=100000,
    description_dict=None,
    decontamination_ngrams_path=None,
    write_out=False,
    output_base_path=None,
    model_prompt=None
):
    """Instantiate and evaluate a model on a list of tasks.

    :param lm: obj
        Language Model
    :param task_dict: dict[str, Task]
        Dictionary of tasks. Tasks will be taken to have name task.EVAL_HARNESS_NAME if defined and type(task).__name__ otherwise.
    :param provide_description: bool
        Not implemented, and this option is deprecated and will be removed in a future version in favor of a different description providing method
    :param num_fewshot: int
        Number of examples in few-shot context
    :param limit: int, optional
        Limit the number of examples per task (only use this for testing)
    :param bootstrap_iters:
        Number of iterations for bootstrap statistics
    :param description_dict: dict[str, str]
        Dictionary of custom task descriptions of the form: `task_name: description`
    :param write_out: bool
        If True, write all prompts, logits and metrics to json for offline analysis
    :param output_base_path: str, optional
        Directory to which detailed eval info will be written. Defaults to present working dir
    :return
        Dictionary of results
    """
    # TODO: completely refactor this entire function to not be a huge mess, ideally breaking it down into smaller pieces

    # TODO: todo: implement proper description-providing system
    assert not provide_description  # not implemented.
    if provide_description is not None:
        # nudge people to not specify it at all
        print(
            "WARNING: provide_description is deprecated and will be removed in a future version in favor of description_dict"
        )

    decontaminate = decontamination_ngrams_path is not None

    task_dict_items = [
        (name, task)
        for name, task in task_dict.items()
        if (task.has_validation_docs() or task.has_test_docs())
    ]

    results = collections.defaultdict(dict)
    versions = collections.defaultdict(dict)

    requests = collections.defaultdict(list)
    turn_requests = collections.defaultdict(dict)
    requests_origin = collections.defaultdict(list)

    overlaps = collections.defaultdict(list)  # {task_name: contaminated_docs}

    # If we ever run into issues where the eval tasks don't fit in memory and we can't afford a machine with bigger
    # memory, we can always modify this plumbing to support that, but I didn't want to include it just yet because
    # over-engineering is bad (or we could make it write the requests to disk and then read them back out again
    #  - probably using an sqlite db because of all the moving parts we have

    # TODO: we need unit tests & sanity checks or something to ensure that the return of `validation_docs` is stable
    docs = {}
    write_out_info = {}

    docs_for_decontamination = collections.defaultdict(list)

    # get lists of each type of request
    for task_name, task in task_dict_items:
        versions[task_name] = task.VERSION
        # default to test doc, fall back to val doc if validation unavailable
        # TODO: the test-fallback-to-val system isn't final, we should revisit it at some point
        # For specific tasks (ccfraud, ccf, taiwan), use validation instead of test
        use_validation_for_these_tasks = ["flare_cra_ccfraud", "flare_cra_ccf", "flare_cra_taiwan"]
        if task_name in use_validation_for_these_tasks:
            if task.has_validation_docs():
                task_doc_func = task.validation_docs
                task_set = "val"  # Required for caching in the decontamination
            elif task.has_test_docs():
                task_doc_func = task.test_docs
                task_set = "test"  # Required for caching in the decontamination
            else:
                raise RuntimeError("Task has neither test_docs nor validation_docs")
        else:
            if task.has_test_docs():
                task_doc_func = task.test_docs
                task_set = "test"  # Required for caching in the decontamination
            elif task.has_validation_docs():
                task_set = "val"  # Required for caching in the decontamination
                task_doc_func = task.validation_docs
            else:
                raise RuntimeError("Task has neither test_docs nor validation_docs")

        # deterministically shuffle docs and chop off the first `limit` because sometimes docs are in some kind of order
        task_docs = list(task_doc_func())
        rnd = random.Random()
        # rnd.seed(42)
        # rnd.shuffle(task_docs)
        print(f"Task: {task_name}; number of docs: {len(task_docs)}")

        if write_out:
            prompt_details = []

        description = (
            description_dict[task_name]
            if description_dict and task_name in description_dict
            else ""
        )
        if limit is not None:
            limit = int(len(task_docs) * limit) if limit < 1.0 else int(limit)

        if model_prompt is None:
            model_prompt = 'no_prompt'

        # for doc_id, doc in enumerate(itertools.islice(task_docs, 0, limit)):
        for doc_id, doc in enumerate(itertools.islice(task_docs, limit)):
            # if "id" in doc:
            #     print("doc-id: ", doc["id"], doc["query"])
            if decontaminate and task.should_decontaminate():
                docs_for_decontamination[(task_name, task_set)].append(
                    task.doc_to_decontamination_query(doc)
                )

            docs[(task_name, doc_id)] = doc
            ctx = task.fewshot_context(
                doc=doc, num_fewshot=num_fewshot, rnd=rnd, description=description
            )

            ctx = MODEL_PROMPT_MAP[model_prompt](ctx)

            reqs = task.construct_requests(doc, ctx)

            if write_out:
                prompt_details.append({"doc_id": doc_id})

            # print the prompt for the first few documents
            # if doc_id < 1:
            #     print(
            #         f"Task: {task_name}; document {doc_id}; context prompt (starting on next line):\n{ctx}\n(end of prompt on previous line)"
            #     )
            #     print("Requests:", reqs)
            # print("================================================")

            if not isinstance(reqs, (list, tuple)):
                reqs = [reqs]
            for i, req in enumerate(reqs):
                requests[req.request_type].append(req)
                # i: index in requests for a single task instance
                # doc_id: unique id that we can get back to a doc using `docs`
                diag_id = doc.get("dialogue_id", doc_id)
                turn = doc.get("turn", 0)
                turn_requests[(diag_id, turn)] = (task_name, doc, doc_id, req)
                requests_origin[req.request_type].append((i, task_name, doc, doc_id, diag_id, turn))
                
                #print("req: " + str(req.args))

                if write_out:
                    prompt_details[-1][f"prompt_{i}"] = "".join(
                        (map(lambda x: "".join(x), req.args))
                    )
            
            #print("request:" + request[])
        if write_out:
            write_out_info[task_name] = prompt_details

    # Compare all tasks/sets at once to ensure a single training set scan
    if decontaminate:
        from lm_eval.decontamination.decontaminate import get_train_overlap

        print("Finding train/test overlap, please wait...")
        overlaps = get_train_overlap(
            docs_for_decontamination, decontamination_ngrams_path, limit
        )

    # all responses for each (task, doc)
    process_res_queue = collections.defaultdict(list)

    # execute each type of request
    for reqtype, reqs in requests.items():
        # TODO: right now, this code runs multiple separate LM requests for multiple Requests differing
        #       only in index. We could implement some kind of caching, but that would be more of a band-aid
        #       solution. we could also implement some kind of auto-grouping here;
        #       they should end up next to each other.

        max_turns = max([val[-1] for val in requests_origin[reqtype]])
        print("Running", reqtype, "requests")
        print(f"Maximum {max_turns} turns")
        task_turns = {}
        for cur_turn in range(max_turns+1):
            print(f"Running {cur_turn}th turn")

            filtered_reqs = []

            for req, (i, task_name, doc, doc_id, diag_id, turn) in zip(reqs, requests_origin[reqtype]
):
                if turn != cur_turn:
                    continue
                task_turns[task_name] = max(turn, task_turns.get(task_name, -1))
                task = task_dict[task_name]
                req = task.reformulate_turn_req(req, [(turn_requests.get((diag_id, t), None), t) for t in range(turn)], turn)
                filtered_reqs.append([req, (i, task_name, doc, doc_id, diag_id, turn)])
            
            print("================================================")
            # print("reqs: ", reqs)
            print("reqtype: ", reqtype)
            # print("[req.args for req in reqs]: ", [req.args for req in reqs])
            
            # For Harbor mode, set request_docs and agent details saving before calling greedy_until
            if reqtype == "greedy_until" and hasattr(lm, 'harbor_mode') and lm.harbor_mode:
                # Enable agent details saving if write_out is enabled
                if write_out:
                    import pathlib
                    lm._save_agent_details = True
                    if output_base_path:
                        output_path = pathlib.Path(output_base_path) if isinstance(output_base_path, str) else output_base_path
                    else:
                        output_path = pathlib.Path(".")
                    lm._agent_log_base_dir = str(output_path / "agent_details")
                    print(f"[DEBUG] Harbor mode: Enabled agent details saving")
                    print(f"[DEBUG]   _save_agent_details: {lm._save_agent_details}")
                    print(f"[DEBUG]   _agent_log_base_dir: {lm._agent_log_base_dir}")
                else:
                    print(f"[DEBUG] Harbor mode: write_out is False, agent details saving disabled")
                
                # Create a list of docs corresponding to each request in filtered_reqs
                # Note: filtered_reqs order matches the order of requests passed to greedy_until
                request_docs = []
                for req, (i, task_name, doc, doc_id, diag_id, turn) in filtered_reqs:
                    request_docs.append(doc)
                # Store docs in lm so greedy_until can access them
                if request_docs:
                    lm._request_docs = request_docs
                else:
                    # Clear if no docs (shouldn't happen, but for safety)
                    if hasattr(lm, '_request_docs'):
                        delattr(lm, '_request_docs')
            
            # Use filtered_reqs instead of reqs to match request_docs
            # filtered_reqs contains only requests for the current turn
            print(f"[DEBUG] filtered_reqs length: {len(filtered_reqs)}")
            print(f"[DEBUG] reqs length: {len(reqs)}")
            if filtered_reqs:
                filtered_req_args = [req[0].args for req in filtered_reqs]
                print(f"[DEBUG] filtered_req_args length: {len(filtered_req_args)}")
                print(f"[DEBUG] filtered_req_args[0] type: {type(filtered_req_args[0]) if filtered_req_args else 'None'}")
                if filtered_req_args and filtered_req_args[0]:
                    print(f"[DEBUG] filtered_req_args[0] value (first 200 chars): {str(filtered_req_args[0])[:200]}")
                    print(f"[DEBUG] filtered_req_args[0] is empty: {not filtered_req_args[0] or (isinstance(filtered_req_args[0], tuple) and len(filtered_req_args[0]) > 0 and not filtered_req_args[0][0])}")
                # print(f"[DEBUG] filtered_req_args content (full): {filtered_req_args}")
                print(f"[DEBUG] About to call {reqtype} with {len(filtered_req_args)} requests")
            else:
                filtered_req_args = []
                print(f"[DEBUG] WARNING: filtered_reqs is empty, using empty list")
            # print(f"[DEBUG] Final filtered_req_args before calling {reqtype}: {filtered_req_args}")
            print(f"[DEBUG] filtered_req_args id: {id(filtered_req_args)}")
            print(f"[DEBUG] filtered_req_args type: {type(filtered_req_args)}")
            print(f"[DEBUG] filtered_req_args len: {len(filtered_req_args) if filtered_req_args else 0}")
            method = getattr(lm, reqtype)
            print(f"[DEBUG] method: {method}")
            print(f"[DEBUG] method type: {type(method)}")
            print(f"[DEBUG] About to call method with filtered_req_args")
            resps = method(filtered_req_args)
            print(f"[DEBUG] After calling method, resps type: {type(resps)}, len: {len(resps) if hasattr(resps, '__len__') else 'N/A'}")
            
            # Clean up _request_docs after use
            if reqtype == "greedy_until" and hasattr(lm, '_request_docs'):
                delattr(lm, '_request_docs')
            print("================end getattr(lm, reqtype)======================")
            resps = [
                x if req[0].index is None else x[req[0].index] for x, req in zip(resps, filtered_reqs
)
            ]

            for resp, req in zip(resps, filtered_reqs):
                i, task_name, doc, doc_id, diag_id, turn = req[1]
                task = task_dict[task_name]
                if not task.EVAL_LAST_TURN or turn == task_turns[task_name]:
                    process_res_queue[(task_name, doc_id)].append((i, resp))
                turn_requests[(diag_id, turn)] = resp

                if write_out:
                    write_out_info[task_name][doc_id][f"logit_{i}"] = resp
                    task = task_dict[task_name]
                    if isinstance(task, lm_eval.base.MultipleChoiceTask):
                        # Convert gold index to actual label string for MultipleChoiceTask
                        if "choices" in doc and isinstance(doc["gold"], int):
                            write_out_info[task_name][doc_id]["truth"] = doc["choices"][doc["gold"]]
                        else:
                            write_out_info[task_name][doc_id]["truth"] = doc["gold"]
                    elif isinstance(task, lm_eval.tasks.winogrande.Winogrande):
                        write_out_info[task_name][doc_id]["truth"] = task.answer_to_num[
                            doc["answer"]
                        ]
                    else:
                        write_out_info[task_name][doc_id]["truth"] = task.doc_to_target(doc)
    vals = collections.defaultdict(list)

    # unpack results and sort back in order and return control to Task
    for (task_name, doc_id), requests in process_res_queue.items():
        requests.sort(key=lambda x: x[0])
        requests = [x[1] for x in requests]

        task = task_dict[task_name]
        doc = docs[(task_name, doc_id)]
        # print("doc: "+ str(doc))
        # print("requests: "+ str(requests))


        metrics = task.process_results(doc, requests)
        
        # Extract pred and gold from process_results for write_out
        if write_out:
            pred = None
            gold = write_out_info[task_name][doc_id].get("truth")
            
            # Check if metrics contain pred information
            # For classification: metrics like f1, macro_f1 contain (pred, gold) tuples
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, tuple) and len(metric_value) >= 2:
                    # Extract pred from tuple (pred, gold, ...)
                    pred = metric_value[0]
                    # Also update gold from tuple if available
                    if len(metric_value) >= 2:
                        gold_from_tuple = metric_value[1]
                        if gold is None or gold != str(gold_from_tuple):
                            gold = str(gold_from_tuple)
                    break
            
            # If no pred found in metrics, try to extract from raw output
            if pred is None and requests:
                # Use the raw model output as pred
                pred = requests[0] if isinstance(requests[0], str) else str(requests[0])
            
            # Store pred and gold
            if pred is not None:
                write_out_info[task_name][doc_id]["pred"] = str(pred)
            if gold is not None:
                write_out_info[task_name][doc_id]["gold"] = str(gold)
                # Also ensure truth field exists
                if "truth" not in write_out_info[task_name][doc_id]:
                    write_out_info[task_name][doc_id]["truth"] = str(gold)
        
        for metric, value in metrics.items():
            vals[(task_name, metric)].append(value)

            if write_out:
                write_out_info[task_name][doc_id][metric] = str(value)

            # Re-use the evaluation for the decontaminated set by just ignoring the overlaps
            if decontaminate and task_name in overlaps:
                if doc_id not in overlaps[task_name]:
                    vals[(task_name, metric + decontaminate_suffix)].append(value)

    # aggregate results
    for (task_name, metric), items in vals.items():
        task = task_dict[task_name]
        real_metric = metric  # key when looking up the metric with task.aggregation
        if metric.endswith(decontaminate_suffix):
            real_metric = metric.replace(
                decontaminate_suffix, ""
            )  # decontaminated still uses the same metric
        
        results[task_name][metric] = task.aggregation()[real_metric](items)
        # hotfix: bleu, chrf, ter seem to be really expensive to bootstrap
        # so we run them less iterations. still looking for a cleaner way to do this

        stderr = lm_eval.metrics.stderr_for_metric(
            metric=task.aggregation()[real_metric],
            bootstrap_iters=min(bootstrap_iters, 1000) if metric in ["bleu", "chrf", "ter"] else bootstrap_iters,
        )

        if stderr is not None:
            results[task_name][metric + "_stderr"] = stderr(items)

    if write_out:
        import json
        import pathlib

        output_base_path = (
            pathlib.Path(output_base_path)
            if output_base_path is not None
            else pathlib.Path(".")
        )
        try:
            output_base_path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            pass

        for task_name, _ in task_dict_items:
            with open(
                output_base_path.joinpath(f"{task_name}_write_out_info.json"),
                "w",
                encoding="utf8",
            ) as fp:
                json.dump(write_out_info[task_name], fp, indent=4, ensure_ascii=False)
        
        # Note: Agent details saving is now enabled before calling greedy_until
        # (moved to earlier in the code to ensure it's set before model execution)

    return {"results": dict(results), "versions": dict(versions)}


def make_table(result_dict):
    """Generate table of results."""
    from pytablewriter import MarkdownTableWriter, LatexTableWriter

    md_writer = MarkdownTableWriter()
    latex_writer = LatexTableWriter()
    md_writer.headers = ["Task", "Version", "Metric", "Value", "", "Stderr"]
    latex_writer.headers = ["Task", "Version", "Metric", "Value", "", "Stderr"]

    values = []

    for k, dic in result_dict["results"].items():
        version = result_dict["versions"][k]
        for m, v in dic.items():
            if m.endswith("_stderr"):
                continue

            if m + "_stderr" in dic:
                se = dic[m + "_stderr"]
                values.append([k, version, m, "%.4f" % v, "±", "%.4f" % se])
            else:
                values.append([k, version, m, "%.4f" % v, "", ""])
            k = ""
            version = ""
    md_writer.value_matrix = values
    latex_writer.value_matrix = values

    # todo: make latex table look good
    # print(latex_writer.dumps())

    return md_writer.dumps()
