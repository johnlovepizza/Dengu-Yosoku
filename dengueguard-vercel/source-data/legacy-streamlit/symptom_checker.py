from pathlib import Path
import pandas as pd
import streamlit as st

QUESTIONNAIRE_DIR = Path(__file__).resolve().parent


def _load_questionnaire_files():
    """Load questionnaire content and rule/message tables from CSV."""
    required = [
        "questions.csv",
        "options.csv",
        "assessment_rules.csv",
        "recommendations.csv",
    ]
    missing = [name for name in required if not (QUESTIONNAIRE_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            "ไม่พบไฟล์ questionnaire: " + ", ".join(missing)
            + f" ในโฟลเดอร์ {QUESTIONNAIRE_DIR}"
        )

    questions = pd.read_csv(QUESTIONNAIRE_DIR / "questions.csv", encoding="utf-8-sig", keep_default_na=False)
    options = pd.read_csv(QUESTIONNAIRE_DIR / "options.csv", encoding="utf-8-sig", keep_default_na=False)
    rules = pd.read_csv(QUESTIONNAIRE_DIR / "assessment_rules.csv", encoding="utf-8-sig", keep_default_na=False)
    recommendations = pd.read_csv(QUESTIONNAIRE_DIR / "recommendations.csv", encoding="utf-8-sig", keep_default_na=False)
    return questions, options, rules, recommendations


def _as_bool(value):
    return bool(value) if value is not None else False


def _parse_optional_number(value, field_label, minimum=None, maximum=None):
    """Return (number, error). Empty values are allowed."""
    if value is None or str(value).strip() == "":
        return None, None
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None, f"{field_label}: กรุณากรอกเป็นตัวเลขเท่านั้น"
    if minimum is not None and number < minimum:
        return None, f"{field_label}: ค่าต่ำกว่าช่วงที่รับได้"
    if maximum is not None and number > maximum:
        return None, f"{field_label}: ค่าสูงกว่าช่วงที่รับได้"
    return number, None


def _recommendation(recommendations, group_code, result_code):
    selected = recommendations[
        (recommendations["group_code"] == group_code)
        & (recommendations["result_code"] == result_code)
    ]
    if selected.empty:
        return {
            "title_th": result_code,
            "message_th": "ไม่พบข้อความคำแนะนำใน recommendations.csv",
            "action_th": "โปรดตรวจสอบไฟล์ CSV",
        }
    row = selected.iloc[0]
    return row.to_dict()


def _show_recommendation(recommendations, group_code, result_code, level="info"):
    item = _recommendation(recommendations, group_code, result_code)
    container = {
        "error": st.error,
        "warning": st.warning,
        "success": st.success,
        "info": st.info,
    }.get(level, st.info)
    container(f"**{item['title_th']}**\n\n{item['message_th']}\n\n**คำแนะนำ:** {item['action_th']}")


def _map_choice_label_to_value(selected_label, options_for_key):
    if selected_label is None:
        return None
    matches = options_for_key[options_for_key["option_label"] == selected_label]
    if matches.empty:
        return None
    return str(matches.iloc[0]["option_value"])


def _page_questions(questions, section_ids):
    """Return questions belonging to the requested wizard page."""
    return questions[questions["section_id"].isin(section_ids)].sort_values(
        ["section_order", "question_order"]
    )


def _store_durable_answer(field, value):
    """Store an answer outside Streamlit's widget lifecycle."""
    answers = dict(st.session_state.get("dq_answers", {}))
    answers[field] = value
    # Reassign the dictionary so Streamlit tracks the state update explicitly.
    st.session_state["dq_answers"] = answers
    # Keep the flat key as a compatibility layer for existing assessment code.
    st.session_state[f"dq_answer_{field}"] = value


def _sync_answer_from_widget(field, widget_type, label_to_value=None):
    """Persist edits immediately, before Streamlit cleans up hidden widgets."""
    widget_key = f"dq_widget_{field}"
    raw_value = st.session_state.get(widget_key)

    if widget_type in ("radio", "select"):
        mapping = label_to_value or {}
        value = mapping.get(raw_value) if raw_value is not None else None
    elif widget_type == "checkbox":
        value = bool(raw_value)
    elif widget_type == "text":
        value = "" if raw_value is None else str(raw_value)
    else:
        value = raw_value

    _store_durable_answer(field, value)


def _render_questions(questions, options, section_ids):
    """Render the requested sections and restore values from durable answers.

    Widgets are intentionally outside st.form. Their on_change callbacks copy
    every change into dq_answer_* immediately, before Streamlit reruns and
    cleans up widgets that are not part of the newly displayed page.
    """
    page_df = _page_questions(questions, section_ids)
    sections = page_df.groupby(
        ["section_id", "section_title", "section_order"], sort=False
    )

    for (section_id, section_title, _), section_questions in sections:
        st.markdown(f"### {section_title}")

        if section_id == "warning":
            st.warning(
                "รายการนี้เป็นสัญญาณเตือนที่ต้องประเมินเร่งด่วนในผู้ที่สงสัย/ยืนยันไข้เลือดออก "
                "แต่การเลือกอาการเพียงข้อเดียว **ไม่ได้ยืนยันว่าเป็นไข้เลือดออก** "
                "ควรไปโรงพยาบาลเพื่อประเมินโดยเร็ว"
            )
        elif section_id == "emergency":
            st.error(
                "อาการเหล่านี้อาจเป็นภาวะฉุกเฉินจากหลายสาเหตุ ไม่จำเพาะต่อไข้เลือดออก "
                "หากเกิดขึ้นให้ไปห้องฉุกเฉินทันที ไม่ต้องรอผลแบบประเมิน"
            )
        elif section_id == "lab":
            st.caption(
                "กรอกเฉพาะผลที่มีจากสถานพยาบาล หากไม่ได้ตรวจให้เลือก 'ไม่ได้ตรวจ / ไม่ทราบ' "
                "หรือเว้นช่องตัวเลขว่าง"
            )

        for _, row in section_questions.iterrows():
            field = row["field_key"]
            label = row["question_th"]
            help_text = row["help_text"] or None
            widget_type = row["input_type"]
            widget_key = f"dq_widget_{field}"
            answer_key = f"dq_answer_{field}"
            durable_answers = st.session_state.setdefault("dq_answers", {})
            saved_value = durable_answers.get(
                field, st.session_state.get(answer_key)
            )

            if widget_type in ("radio", "select"):
                option_rows = options[
                    options["options_key"] == row["options_key"]
                ].sort_values("display_order")
                labels = option_rows["option_label"].astype(str).tolist()
                label_to_value = dict(zip(
                    option_rows["option_label"].astype(str),
                    option_rows["option_value"].astype(str),
                ))

                # Restore stable option_value as the visible option_label.
                selected_label = None
                if saved_value is not None:
                    for option_label, option_value in label_to_value.items():
                        if option_value == str(saved_value):
                            selected_label = option_label
                            break

                if field in durable_answers:
                    # Always restore from the durable answer store when this page is rendered.
                    st.session_state[widget_key] = selected_label
                elif widget_key not in st.session_state:
                    st.session_state[widget_key] = None

                callback_args = (field, widget_type, label_to_value)
                if widget_type == "radio":
                    st.radio(
                        label,
                        labels,
                        index=None,
                        key=widget_key,
                        help=help_text,
                        on_change=_sync_answer_from_widget,
                        args=callback_args,
                    )
                else:
                    st.selectbox(
                        label,
                        labels,
                        index=None,
                        placeholder=row["placeholder"] or "เลือกคำตอบ",
                        key=widget_key,
                        help=help_text,
                        on_change=_sync_answer_from_widget,
                        args=callback_args,
                    )

            elif widget_type == "checkbox":
                if field in durable_answers:
                    st.session_state[widget_key] = bool(saved_value)
                elif widget_key not in st.session_state:
                    st.session_state[widget_key] = False
                st.checkbox(
                    label,
                    key=widget_key,
                    help=help_text,
                    on_change=_sync_answer_from_widget,
                    args=(field, widget_type, None),
                )

            elif widget_type == "text":
                if field in durable_answers:
                    st.session_state[widget_key] = "" if saved_value is None else str(saved_value)
                elif widget_key not in st.session_state:
                    st.session_state[widget_key] = ""
                st.text_input(
                    label,
                    placeholder=row["placeholder"] or "",
                    key=widget_key,
                    help=help_text,
                    on_change=_sync_answer_from_widget,
                    args=(field, widget_type, None),
                )


def _save_page_answers(questions, options, section_ids):
    """Persist every currently rendered value before changing wizard pages."""
    page_df = _page_questions(questions, section_ids)

    for _, row in page_df.iterrows():
        field = row["field_key"]
        widget_key = f"dq_widget_{field}"
        widget_type = row["input_type"]

        # If Streamlit has no live widget value, retain the last durable answer.
        if widget_key not in st.session_state:
            continue

        raw_value = st.session_state.get(widget_key)

        if widget_type in ("radio", "select"):
            option_rows = options[
                options["options_key"] == row["options_key"]
            ]
            value = _map_choice_label_to_value(raw_value, option_rows)
        elif widget_type == "checkbox":
            value = bool(raw_value)
        elif widget_type == "text":
            value = "" if raw_value is None else str(raw_value)
        else:
            value = raw_value

        _store_durable_answer(field, value)


def _collect_all_answers(questions):
    """Build assessment inputs from durable per-session answers."""
    durable_answers = st.session_state.setdefault("dq_answers", {})
    result = {}
    for field in questions["field_key"].tolist():
        if field in durable_answers:
            result[field] = durable_answers[field]
        else:
            result[field] = st.session_state.get(f"dq_answer_{field}")
    return result


def _navigate_back(questions, options, section_ids, target_page):
    """Save the visible page before navigating backwards."""
    _save_page_answers(questions, options, section_ids)
    st.session_state["dq_page_index"] = target_page
    st.session_state.pop("dq_navigation_error", None)


def _navigate_forward(questions, options, section_ids, current_page, page_count):
    """Save the visible page, validate required fields, then advance."""
    _save_page_answers(questions, options, section_ids)
    answers = _collect_all_answers(questions)

    if current_page == 0:
        if answers.get("fever_status") is None:
            st.session_state["dq_navigation_error"] = (
                "กรุณาระบุสถานะการมีไข้ก่อนดำเนินการต่อ"
            )
            return

        fever_present_or_recent = answers.get("fever_status") in (
            "fever_now", "fever_reduced"
        )
        if fever_present_or_recent and answers.get("illness_onset") is None:
            st.session_state["dq_navigation_error"] = (
                "กรุณาระบุระยะเวลาตั้งแต่เริ่มป่วย"
            )
            return

    st.session_state.pop("dq_navigation_error", None)
    if current_page < page_count - 1:
        st.session_state["dq_page_index"] = current_page + 1
    else:
        st.session_state["dq_show_results"] = True


def _reset_questionnaire_state(questions):
    """Clear all questionnaire answers and navigation state for a fresh run."""
    keys_to_delete = [
        key for key in list(st.session_state.keys())
        if key.startswith("dq_widget_") or key.startswith("dq_answer_")
    ]
    for key in keys_to_delete:
        del st.session_state[key]
    st.session_state.pop("dq_answers", None)
    st.session_state.pop("dq_navigation_error", None)
    st.session_state["dq_page_index"] = 0
    st.session_state["dq_show_results"] = False

def _clinical_manifestation_count(a):
    """Count WHO-compatible clinical manifestation groups, not every checkbox."""
    groups = [
        bool(a.get("headache") or a.get("eye_pain")),
        bool(a.get("myalgia")),
        bool(a.get("nausea_vomiting")),
        bool(a.get("rash")),
        bool(a.get("petechiae")),
        bool(a.get("leukopenia_reported")),
    ]
    return sum(groups)


def render_symptom_checker():
    questions, options, rules, recommendations = _load_questionnaire_files()

    st.title("Dengue Symptom Checker")
    st.subheader("ระบบคัดกรองอาการและข้อมูลสนับสนุนโรคไข้เลือดออก")
    st.write(
        "แบบสอบถามนี้แยกการประเมินความเร่งด่วนออกจากระดับข้อมูลที่สนับสนุนไข้เลือดออก "
        "เพราะสัญญาณเตือนหรืออาการทั่วไปเพียงอย่างเดียวไม่สามารถยืนยันสาเหตุของโรคได้"
    )
    st.info(
        "เป็นเครื่องมือคัดกรองและให้ข้อมูลเบื้องต้น ไม่ใช่เครื่องมือวินิจฉัย "
        "หากมีอาการฉุกเฉินให้ไปโรงพยาบาลทันทีโดยไม่ต้องกรอกแบบสอบถาม"
    )

    # Wizard layout:
    # Page 1: section 1 (fever and illness timeline)
    # Page 2: sections 2–7 (symptoms, warning signs, emergency,
    #         exposure, personal risks, and hydration)
    # Page 3: section 8 (optional laboratory results)
    # Final step: integrated assessment results.
    wizard_pages = [
        {"sections": ["fever"], "label": "1", "title": "สถานะไข้และระยะเวลาป่วย"},
        {
            "sections": [
                "symptoms", "warning", "emergency", "exposure",
                "personal", "hydration"
            ],
            "label": "2–7",
            "title": "อาการและข้อมูลประกอบการประเมิน (ข้อ 2–7)"
        },
        {
            "sections": ["lab"],
            "label": "8",
            "title": "ผลตรวจทางห้องปฏิบัติการ (ถ้ามี)"
        },
    ]

    st.session_state.setdefault("dq_answers", {})
    st.session_state.setdefault("dq_page_index", 0)
    st.session_state.setdefault("dq_show_results", False)
    page_index = min(max(int(st.session_state["dq_page_index"]), 0), len(wizard_pages) - 1)
    show_results = bool(st.session_state["dq_show_results"])

    # Display the progress/navigation indicator.
    step_labels = [page["label"] for page in wizard_pages] + ["ผลการประเมิน"]
    current_step = len(wizard_pages) if show_results else page_index
    total_steps = len(step_labels)
    st.progress((current_step + 1) / total_steps)

    # Compact stepper makes the requested page order visible at a glance.
    step_cols = st.columns(total_steps)
    for step_number, (step_col, step_label) in enumerate(zip(step_cols, step_labels)):
        with step_col:
            if step_number < current_step:
                st.markdown(f"✅ **{step_label}**")
            elif step_number == current_step:
                st.markdown(f"**🔵 {step_label}**")
            else:
                st.caption(step_label)

    if show_results:
        st.caption(f"ขั้นตอน {total_steps} จาก {total_steps} · ผลการประเมิน")
        st.markdown("### ผลการประเมินเบื้องต้น")
    else:
        current_page = wizard_pages[page_index]
        st.caption(
            f"ขั้นตอน {page_index + 1} จาก {total_steps} · "
            f"ส่วน {current_page['label']} — {current_page['title']}"
        )
        st.markdown(f"## {current_page['title']}")
        if page_index == 1:
            st.caption(
                "หน้านี้รวมคำถามข้อ 2–7 ไว้ด้วยกัน "
                "สามารถเลื่อนหน้าจอลงเพื่อตอบคำถามในแต่ละหมวด "
                "จากนั้นกด ‘ถัดไป’ เพื่อไปยังหน้าผลตรวจทางห้องปฏิบัติการ"
            )
        elif page_index == 2:
            st.caption(
                "หน้านี้แยกผลตรวจทางห้องปฏิบัติการออกจากคำถามอาการ "
                "สามารถเว้นว่างหรือข้ามการกรอกผลตรวจได้ หากไม่มีผลตรวจจากสถานพยาบาล "
                "จากนั้นกด ‘ประเมินผล’ เพื่อดูผลการคัดกรอง"
            )

        # Render widgets outside a form. Each widget's on_change callback stores
        # its value in dq_answer_* immediately, so answers survive page changes.
        _render_questions(questions, options, current_page["sections"])
        st.divider()

        nav_error = st.session_state.pop("dq_navigation_error", None)
        if nav_error:
            st.error(nav_error)

        if page_index == 0:
            st.button(
                "ถัดไป  →",
                type="primary",
                use_container_width=True,
                key="dq_next_page_0",
                on_click=_navigate_forward,
                args=(questions, options, current_page["sections"], page_index, len(wizard_pages)),
            )
        else:
            back_col, next_col = st.columns(2)
            with back_col:
                st.button(
                    "←  ย้อนกลับ",
                    use_container_width=True,
                    key=f"dq_back_page_{page_index}",
                    on_click=_navigate_back,
                    args=(questions, options, current_page["sections"], page_index - 1),
                )
            with next_col:
                next_label = "ประเมินผล  →" if page_index == len(wizard_pages) - 1 else "ถัดไป  →"
                st.button(
                    next_label,
                    type="primary",
                    use_container_width=True,
                    key=f"dq_next_page_{page_index}",
                    on_click=_navigate_forward,
                    args=(questions, options, current_page["sections"], page_index, len(wizard_pages)),
                )

        return

    # At the results step, all answers have been copied to durable session state.
    answers = _collect_all_answers(questions)

    # Input validation: fever status is required; onset is required when fever is present/recent.
    if answers.get("fever_status") is None:
        st.error("กรุณาระบุสถานะการมีไข้ก่อนประเมิน")
        return

    fever_present_or_recent = answers.get("fever_status") in ("fever_now", "fever_reduced")
    if fever_present_or_recent and answers.get("illness_onset") is None:
        st.error("กรุณาระบุระยะเวลาตั้งแต่เริ่มป่วย")
        return

    # Parse optional numeric fields and validate them without treating them as diagnostic cut-offs.
    numeric_specs = {
        "temperature_c": (30, 45, "อุณหภูมิร่างกาย"),
        "platelet_current": (0, 2000000, "Platelet ปัจจุบัน"),
        "platelet_previous": (0, 2000000, "Platelet ครั้งก่อน"),
        "hct_current": (0, 100, "Hct ปัจจุบัน"),
        "hct_previous": (0, 100, "Hct ครั้งก่อน"),
        "wbc_current": (0, 200000, "WBC"),
    }
    numeric_values = {}
    numeric_errors = []
    for field, (minimum, maximum, label) in numeric_specs.items():
        value, error = _parse_optional_number(
            answers.get(field), label, minimum=minimum, maximum=maximum
        )
        numeric_values[field] = value
        if error:
            numeric_errors.append(error)
    if numeric_errors:
        for error in numeric_errors:
            st.error(error)
        return

    # Collect safety signals independently from dengue evidence.
    emergency_items = {
        "อาเจียนเป็นเลือดหรือถ่ายอุจจาระเป็นเลือด": _as_bool(answers.get("blood_in_vomit_stool")),
        "หายใจเร็วหรือหายใจลำบาก": _as_bool(answers.get("breathing_difficulty")),
        "มือเท้าเย็น ตัวซีด เหงื่อออกเย็น หรือคล้ายจะเป็นลม": _as_bool(answers.get("cold_clammy_faint")),
        "สับสนมาก ปลุกไม่ตื่น ชัก หรือหมดสติ": _as_bool(answers.get("altered_consciousness")),
    }
    emergency_found = [name for name, selected in emergency_items.items() if selected]

    warning_items = {
        "ปวดท้องรุนแรงหรือกดเจ็บบริเวณท้อง": _as_bool(answers.get("severe_abdominal")),
        "อาเจียนต่อเนื่องตามเกณฑ์ที่ระบุ": _as_bool(answers.get("persistent_vomiting")),
        "มีเลือดออกตามเยื่อบุ": _as_bool(answers.get("mucosal_bleeding")),
        "ซึมลง อ่อนเพลียมากผิดปกติ หรือกระสับกระส่าย": _as_bool(answers.get("lethargy_restlessness")),
        "ท้องโต/บวมใหม่ หรือได้รับแจ้งว่ามีของเหลวสะสม": _as_bool(answers.get("fluid_accumulation")),
    }
    warning_found = [name for name, selected in warning_items.items() if selected]

    hydration_found = []
    if _as_bool(answers.get("unable_to_drink")):
        hydration_found.append("ไม่สามารถดื่มน้ำหรือรับประทานอาหารได้ตามปกติ")
    if _as_bool(answers.get("reduced_urine")):
        hydration_found.append("ปัสสาวะน้อยลงอย่างชัดเจน")
    if _as_bool(answers.get("excessive_thirst")):
        hydration_found.append("กระหายน้ำมากผิดปกติ")

    # Dengue clinical suspicion is assessed separately. Warning signs do NOT establish dengue.
    exposure_to_transmission_area = _as_bool(answers.get("endemic_area"))
    onset_2_to_7_days = answers.get("illness_onset") in ("day2_3", "day4_5", "day6_7")
    compatible_manifestations = _clinical_manifestation_count(answers)
    clinical_pattern = (
        fever_present_or_recent
        and onset_2_to_7_days
        and exposure_to_transmission_area
        and compatible_manifestations >= 2
    )

    # Interpret dengue laboratory evidence by test type; never treat all positive tests equally.
    naat_positive = answers.get("naat_result") == "positive"
    ns1_positive = answers.get("ns1_result") == "positive"
    igm_positive = answers.get("igm_result") == "positive"
    igg_positive = answers.get("igg_result") == "positive"

    # Independent result display: urgency and dengue evidence are both shown.
    st.divider()
    st.header("ผลการประเมินเบื้องต้น")

    st.markdown("### A. ความเร่งด่วนในการรับการประเมิน")
    if emergency_found:
        _show_recommendation(recommendations, "urgency", "EMERGENCY", "error")
        st.markdown("**อาการฉุกเฉินที่เลือก:**")
        for item in emergency_found:
            st.markdown(f"- {item}")
        st.error("ไม่ต้องรอผลการประเมินส่วนอื่น ให้ไปห้องฉุกเฉินทันที; หากเดินทางเองไม่ปลอดภัย โทร 1669")
    elif warning_found:
        _show_recommendation(recommendations, "urgency", "DENGUE_WARNING", "warning")
        st.markdown("**สัญญาณเตือนที่เลือก:**")
        for item in warning_found:
            st.markdown(f"- {item}")
        st.caption(
            "ข้อสำคัญ: การพบสัญญาณเตือนทำให้ต้องประเมินความเร่งด่วน "
            "แต่ไม่ได้ทำให้ระบบสรุปว่าเป็นไข้เลือดออกโดยอัตโนมัติ"
        )
    elif any(_as_bool(answers.get(k)) for k in ("unable_to_drink", "reduced_urine")):
        _show_recommendation(recommendations, "urgency", "HYDRATION_REVIEW", "warning")
        for item in hydration_found:
            st.markdown(f"- {item}")
    elif fever_present_or_recent:
        _show_recommendation(recommendations, "urgency", "FEVER_REVIEW", "warning")
    else:
        _show_recommendation(recommendations, "urgency", "NO_URGENT_FLAG", "info")
        if hydration_found:
            st.write("ข้อมูลเรื่องการดื่มน้ำ/ปัสสาวะที่เลือก:")
            for item in hydration_found:
                st.markdown(f"- {item}")

    # Personal risk factors alter the need for clinical follow-up, not dengue probability by themselves.
    personal_risks = {
        "กำลังตั้งครรภ์": _as_bool(answers.get("pregnancy")),
        "มีโรคประจำตัว": _as_bool(answers.get("chronic_disease")),
        "มีความผิดปกติของการแข็งตัวของเลือด/เลือดออกง่าย": _as_bool(answers.get("bleeding_disorder")),
        "เป็นเด็กอายุต่ำกว่า 1 ปีหรือผู้สูงอายุตั้งแต่ 65 ปีขึ้นไป": _as_bool(answers.get("age_risk")),
    }
    personal_found = [name for name, selected in personal_risks.items() if selected]
    if personal_found:
        st.markdown("**ปัจจัยสุขภาพที่ควรแจ้งบุคลากรทางการแพทย์:**")
        for item in personal_found:
            st.markdown(f"- {item}")

    st.markdown("### B. ระดับข้อมูลที่สนับสนุนความสงสัยไข้เลือดออก")
    if naat_positive:
        _show_recommendation(recommendations, "dengue_evidence", "LAB_SUPPORT_NAAT", "success")
    elif ns1_positive:
        _show_recommendation(recommendations, "dengue_evidence", "LAB_SUPPORT_NS1", "success")
        if answers.get("ns1_method") in (None, "unknown"):
            st.info("ไม่ทราบวิธีตรวจ NS1: ควรตรวจสอบชื่อชุดตรวจ วิธีตรวจ และข้อกำหนดของผู้ผลิตก่อนสรุปผล")
    elif igm_positive:
        _show_recommendation(recommendations, "dengue_evidence", "PRESUMPTIVE_RECENT", "warning")
    elif clinical_pattern:
        _show_recommendation(recommendations, "dengue_evidence", "CLINICAL_SUSPICION", "warning")
    elif igg_positive:
        _show_recommendation(recommendations, "dengue_evidence", "IGG_ONLY", "info")
    else:
        _show_recommendation(recommendations, "dengue_evidence", "INSUFFICIENT", "info")

    # Interpret every reported dengue assay separately; do not add arbitrary points.
    lab_interpretations = []
    if naat_positive:
        lab_interpretations.append(("RT-PCR/NAAT Positive", "เป็นหลักฐานตรวจพบสารพันธุกรรมของไวรัสเดงกีในตัวอย่างที่ตรวจ และสนับสนุนการติดเชื้อปัจจุบันอย่างมาก"))
    if ns1_positive:
        lab_interpretations.append(("NS1 Positive", "เป็นหลักฐานสนับสนุนการติดเชื้อเดงกีระยะเฉียบพลัน ควรตรวจสอบชนิดชุดตรวจ วิธีตรวจ และข้อกำหนดของผู้ผลิต"))
    if igm_positive:
        lab_interpretations.append(("IgM Positive", "สนับสนุนการติดเชื้อเดงกีเมื่อไม่นานมานี้ (presumptive recent infection); อาจเกิดปฏิกิริยาข้ามกับ flavivirus อื่นได้"))
    if igg_positive:
        lab_interpretations.append(("IgG Positive", "IgG จากตัวอย่างเดียวไม่ยืนยันการติดเชื้อเฉียบพลัน อาจสะท้อนการติดเชื้อเดิมหรือปฏิกิริยาข้าม"))
    if lab_interpretations:
        st.markdown("**การแปลผลรายการตรวจที่เป็นบวก:**")
        for test_name, interpretation in lab_interpretations:
            st.markdown(f"- **{test_name}:** {interpretation}")

    if answers.get("lab_timing") == "day1_3" and answers.get("igm_result") == "negative":
        st.info("IgM อาจยังตรวจไม่พบในช่วงต้นของการป่วย ผล IgM ลบในช่วงนี้จึงไม่สามารถตัดไข้เลือดออกได้")
    if answers.get("lab_timing") in ("day1_3", "day4_7") and answers.get("ns1_result") == "negative" and answers.get("naat_result") == "negative":
        st.info("ผล NS1/NAAT ลบไม่สามารถตัดไข้เลือดออกได้ทั้งหมด ควรให้แพทย์พิจารณาระยะเวลาป่วยและความจำเป็นในการตรวจซ้ำ/ตรวจเพิ่มเติม")

    # CBC is used as supporting context/trend only, not as an automatic diagnosis or severity score.
    st.markdown("### C. ข้อมูล CBC ประกอบการประเมิน")
    cbc_values = []
    for key, label, unit in [
        ("platelet_current", "Platelet ปัจจุบัน", "cells/µL"),
        ("hct_current", "Hct ปัจจุบัน", "%"),
        ("wbc_current", "WBC ปัจจุบัน", "cells/µL"),
    ]:
        value = numeric_values.get(key)
        if value is not None:
            st.write(f"{label}: {value:g} {unit}")
            cbc_values.append(value)

    platelet_now = numeric_values.get("platelet_current")
    platelet_prev = numeric_values.get("platelet_previous")
    hct_now = numeric_values.get("hct_current")
    hct_prev = numeric_values.get("hct_previous")
    if platelet_now is not None and platelet_prev is not None:
        if platelet_now < platelet_prev:
            st.warning("Platelet ที่กรอกครั้งปัจจุบันต่ำกว่าครั้งก่อน ควรให้แพทย์ประเมินแนวโน้มร่วมกับอาการและช่วงอ้างอิงของห้องปฏิบัติการ")
        elif platelet_now > platelet_prev:
            st.info("Platelet ที่กรอกครั้งปัจจุบันสูงกว่าครั้งก่อน การแปลผลต้องพิจารณาบริบทและช่วงเวลาที่ตรวจ")
        else:
            st.info("Platelet เท่ากับค่าครั้งก่อนตามข้อมูลที่กรอก")
    if hct_now is not None and hct_prev is not None:
        if hct_now > hct_prev:
            st.warning("Hct ที่กรอกครั้งปัจจุบันสูงกว่าครั้งก่อน ควรให้แพทย์พิจารณาร่วมกับภาวะสารน้ำและผล CBC อื่น")
        elif hct_now < hct_prev:
            st.info("Hct ที่กรอกครั้งปัจจุบันต่ำกว่าครั้งก่อน การแปลผลต้องพิจารณาบริบททางคลินิก")
        else:
            st.info("Hct เท่ากับค่าครั้งก่อนตามข้อมูลที่กรอก")
    if _as_bool(answers.get("leukopenia_reported")):
        st.info("มีการระบุ Leukopenia ในใบรายงาน ซึ่งเป็นข้อมูลทางห้องปฏิบัติการที่อาจสนับสนุนการพิจารณาไข้เลือดออกเมื่อใช้ร่วมกับไข้ ประวัติระบาดวิทยา และอาการอื่น แต่ไม่จำเพาะต่อไข้เลือดออก")
    if cbc_values:
        st.caption("ระบบแสดงค่าที่กรอกและเปรียบเทียบแนวโน้มเบื้องต้นเท่านั้น ไม่ได้ใช้ cut-off เดี่ยว ๆ เพื่อวินิจฉัยหรือจัดระดับความรุนแรง ต้องเทียบช่วงอ้างอิงและข้อมูลทางคลินิก")
    else:
        st.write("ไม่ได้ระบุผล CBC")

    st.markdown("### D. ข้อควรพิจารณาเกี่ยวกับสาเหตุอื่น")
    has_general_symptoms = any(
        _as_bool(answers.get(key))
        for key in (
            "headache", "eye_pain", "myalgia", "nausea_vomiting", "rash",
            "fatigue", "poor_appetite", "petechiae", "abdominal_discomfort"
        )
    )
    if naat_positive or ns1_positive:
        st.info(
            "ผลตรวจที่เลือกสนับสนุนการติดเชื้อเดงกี แต่แบบสอบถามไม่สามารถประเมินภาวะร่วม "
            "หรือสาเหตุอื่นทั้งหมดได้ หากมีอาการผิดปกติที่ไม่สอดคล้องหรือรุนแรงขึ้น ให้แพทย์ประเมินเพิ่มเติม"
        )
    elif fever_present_or_recent or has_general_symptoms:
        _show_recommendation(recommendations, "other_cause", "OTHER_CAUSES_POSSIBLE", "info")
    else:
        st.info(
            "ยังไม่พบอาการทั่วไปจากรายการที่เลือก และยังไม่มีผลตรวจที่สนับสนุนไข้เลือดออก "
            "ผลนี้ไม่สามารถยืนยันว่าไม่มีการติดเชื้อได้"
        )

    # Summary of key inputs for transparency.
    st.markdown("### E. สรุปข้อมูลที่ได้รับ")
    st.write(f"สถานะไข้: {answers.get('fever_status') or 'ไม่ได้ระบุ'}")
    st.write(f"ระยะเวลาตั้งแต่เริ่มป่วย: {answers.get('illness_onset') or 'ไม่ได้ระบุ'}")
    st.write(f"จำนวนกลุ่มอาการที่เข้าได้กับเกณฑ์ทางคลินิก: {compatible_manifestations} กลุ่ม")
    st.write(f"ประวัติอยู่/เดินทางในพื้นที่แพร่เชื้อใน 14 วัน: {'มี' if exposure_to_transmission_area else 'ไม่ได้เลือก'}")

    # Self-care is secondary and must never override urgent advice.
    st.divider()
    st.markdown("### คำแนะนำทั่วไป")
    if emergency_found or warning_found:
        st.error("ให้ปฏิบัติตามคำแนะนำให้ไปโรงพยาบาลข้างต้นก่อน ไม่ควรใช้การดูแลตนเองแทนการรักษา")
    else:
        st.markdown(
            "- พักผ่อนและดื่มน้ำตามความเหมาะสม หากไม่มีข้อจำกัดน้ำจากแพทย์\n"
            "- หากมีไข้และสงสัยไข้เลือดออก ให้ปรึกษาแพทย์/เภสัชกรเรื่องยาลดไข้; หลีกเลี่ยง aspirin และ NSAIDs เช่น ibuprofen จนกว่าจะได้รับคำแนะนำทางการแพทย์\n"
            "- ป้องกันไม่ให้ยุงกัด เพื่อลดการแพร่เชื้อหากเป็นไข้เลือดออก\n"
            "- หากมีอาการเตือนหรืออาการรุนแรงขึ้น ให้ไปโรงพยาบาลทันที"
        )

    with st.expander("ดูหลักเกณฑ์และแหล่งอ้างอิงที่ใช้ในการออกแบบ"):
        st.caption("ตารางนี้อธิบายหลักการคัดกรองที่เชื่อมกับ Assessment Engine ใน Python ไม่ใช่เกณฑ์วินิจฉัยอัตโนมัติ")
        for _, rule in rules.sort_values(["domain", "priority"]).iterrows():
            st.markdown(f"**{rule['rule_id']} · {rule['logic_summary_th']}**")
            st.caption(f"ข้อควรระวัง: {rule['clinical_note_th']}")
            if rule["reference_url"]:
                st.markdown(f"แหล่งอ้างอิง: {rule['reference_url']}")

    st.caption(
        "ข้อจำกัด: ผลนี้เป็นการคัดกรอง ไม่ใช่การวินิจฉัยหรือคะแนนความน่าจะเป็น "
        "เกณฑ์ในโค้ดเป็นกฎช่วยจัดกลุ่มเบื้องต้น ควรให้แพทย์/ผู้เชี่ยวชาญตรวจสอบก่อนใช้กับผู้ป่วยจริง "
        "และผลตรวจต้องแปลผลตามวิธีตรวจ ชุดตรวจ ระยะเวลาป่วย และช่วงอ้างอิงของห้องปฏิบัติการ"
    )

    st.divider()
    # The results page intentionally offers only a full reset, as requested.
    if st.button(
        "ทำแบบประเมินใหม่",
        type="primary",
        use_container_width=True,
        key="dq_restart_from_results",
    ):
        _reset_questionnaire_state(questions)
        st.rerun()
