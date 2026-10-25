"""Study planning tool and optional OpenAI tool-calling agent.

The basic planner is deterministic Python. The optional OpenAI mode uses an LLM
to interpret the request and call the create_study_plan tool.
"""
import json
from datetime import date, timedelta
from urllib.parse import quote_plus


def create_study_plan(subjects, total_minutes, days=3, start_date=None,
                      break_minutes=5, goal=""):
    """Create a simple schedule by distributing study time across subjects and days."""
    if not isinstance(subjects, list) or not subjects:
        raise ValueError("subjects must be a non-empty list")
    subjects = [str(s).strip() for s in subjects if str(s).strip()]
    if not subjects:
        raise ValueError("Please provide at least one non-empty subject.")
    if int(total_minutes) < 15:
        raise ValueError("total_minutes must be at least 15")
    if not 1 <= int(days) <= 14:
        raise ValueError("days must be between 1 and 14")
    if not 0 <= int(break_minutes) <= 30:
        raise ValueError("break_minutes must be between 0 and 30")

    start = date.fromisoformat(start_date) if start_date else date.today()
    total_minutes = int(total_minutes)
    days = int(days)
    break_minutes = int(break_minutes)

    # Divide the available study minutes evenly over days, then rotate subjects.
    minutes_per_day = [total_minutes // days] * days
    for i in range(total_minutes % days):
        minutes_per_day[i] += 1

    schedule = []
    for day_index, day_minutes in enumerate(minutes_per_day):
        current_date = start + timedelta(days=day_index)
        # Split each day's time across a rotating subset of subjects.
        # Every day gets at least one subject; minutes are allocated as evenly as possible.
        subject_count = min(len(subjects), max(1, min(3, len(subjects))))
        chosen = [subjects[(day_index * subject_count + j) % len(subjects)]
                  for j in range(subject_count)]
        each = day_minutes // subject_count
        remainder = day_minutes % subject_count
        tasks = []
        for j, subject in enumerate(chosen):
            duration = each + (1 if j < remainder else 0)
            if duration <= 0:
                continue
            activity = "Review key concepts, then solve practice questions."
            if goal:
                activity = f"{goal.strip()} Focus on {subject}."
            tasks.append({
                "subject": subject,
                "duration_minutes": duration,
                "activity": activity
            })
        schedule.append({
            "day": day_index + 1,
            "date": current_date.isoformat(),
            "total_minutes": day_minutes,
            "tasks": tasks,
            "note": f"Take a {break_minutes}-minute break between study blocks when practical."
        })

    return {
        "summary": f"{total_minutes} study minutes distributed across {days} day(s) for {len(subjects)} subject(s).",
        "subjects": subjects,
        "total_minutes": total_minutes,
        "days": days,
        "goal": goal,
        "schedule": schedule,
        "tips": [
            "Start each session by recalling what you already know.",
            "Use active recall and practice questions instead of only rereading.",
            "Adjust the plan if a subject needs more time."
        ]
    }


def run_openai_agent_normal(request, api_key):
    """Use OpenAI tool calling to let an LLM call the deterministic study planner."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    tool_schema = {
        "type": "function",
        "function": {
            "name": "create_study_plan",
            "description": "Create a safe study schedule using the student's subjects, available minutes, days, start date, breaks, and goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subjects": {"type": "array", "items": {"type": "string"}},
                    "total_minutes": {"type": "integer", "minimum": 15, "maximum": 720},
                    "days": {"type": "integer", "minimum": 1, "maximum": 14},
                    "start_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "break_minutes": {"type": "integer", "minimum": 0, "maximum": 30},
                    "goal": {"type": "string"}
                },
                "required": ["subjects", "total_minutes", "days", "start_date", "break_minutes", "goal"],
                "additionalProperties": False
            }
        }
    }

    system_prompt = (
        "You are a helpful study-planning assistant. Use the create_study_plan tool to make "
        "the schedule; do not invent subjects or available time. If the request has the supplied "
        "fields, call the tool. Explain the resulting schedule briefly and encourage the student "
        "to adapt it to their syllabus. The tool result is authoritative for schedule data."
    )
    user_message = (
        "Create a study plan from this student information:\n"
        + json.dumps(request, ensure_ascii=False)
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        tools=[tool_schema],
        tool_choice={"type": "function", "function": {"name": "create_study_plan"}},
        temperature=0.2,
    )

    message = response.choices[0].message
    if not message.tool_calls:
        raise RuntimeError("The model did not request the study-plan tool.")

    tool_call = message.tool_calls[0]
    if tool_call.function.name != "create_study_plan":
        raise RuntimeError("The model requested an unexpected tool.")

    args = json.loads(tool_call.function.arguments)
    # Validate and execute locally; never execute arbitrary code generated by the model.
    result = create_study_plan(**args)
    result["ai_explanation"] = (
        message.content.strip() if message.content else
        "The AI selected the study-plan tool; the schedule was generated and validated by Python."
    )
    return result


def run_openai_agent(request, api_key):
    """Run the LLM-powered personalized learning-roadmap agent."""
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        timeout=60,
        max_retries=2,
    )

    result = generate_learning_roadmap(
        request=request,
        client=client,
        model="gpt-4o-mini",
    )

    result["ai_explanation"] = (
        "The LLM designed the learning sequence, and Python "
        "validated the roadmap and calculated the study schedule."
    )

    return result



def generate_learning_roadmap(request, client, model="gpt-4o-mini"):
    """
    Generate a personalized learning roadmap using OpenAI.

    Includes:
    - Learning topics and objectives
    - Daily study schedule
    - 5 recommended books
    - 5 YouTube learning searches
    - Additional learning resource links

    Args:
        request (dict): Student study requirements.
        client: Initialized OpenAI client.
        model (str): OpenAI model name.

    Returns:
        dict: Roadmap and resources for the Streamlit UI.
    """

    # --------------------------------------------------
    # 1. Read and validate student input
    # --------------------------------------------------
    subjects = request.get("subjects", [])

    if not isinstance(subjects, list):
        raise ValueError("Subjects must be provided as a list.")

    subjects = [
        str(subject).strip()
        for subject in subjects
        if str(subject).strip()
    ]

    if not subjects:
        raise ValueError("Please provide at least one subject.")

    try:
        total_minutes = int(request.get("total_minutes", 300))
        days = int(request.get("days", 5))
        break_minutes = int(request.get("break_minutes", 5))
    except (TypeError, ValueError):
        raise ValueError(
            "Study minutes, days, and break minutes must be numbers."
        )

    if not 15 <= total_minutes <= 10080:
        raise ValueError("Total study time must be between 15 and 10080 minutes.")

    if not 1 <= days <= 14:
        raise ValueError("Study duration must be between 1 and 14 days.")

    if not 0 <= break_minutes <= 30:
        raise ValueError("Break duration must be between 0 and 30 minutes.")

    start_date_text = request.get("start_date")

    if start_date_text:
        try:
            start_date = date.fromisoformat(start_date_text)
        except (TypeError, ValueError):
            raise ValueError("Start date must use YYYY-MM-DD format.")
    else:
        start_date = date.today()

    goal = str(request.get("goal", "")).strip()
    level = str(request.get("level", "Beginner")).strip()

    # --------------------------------------------------
    # 2. Ask OpenAI to create the learning roadmap
    # --------------------------------------------------
    system_prompt = """
You are an expert educational planner and learning-resource advisor.

Create a personalized, practical learning roadmap based only on the
subjects and study requirements supplied by the student.

Return valid JSON only, using this structure:

{
  "summary": "Short roadmap summary",
  "topics": [
    {
      "title": "Topic name",
      "objective": "What the student should learn",
      "concepts": ["Concept 1", "Concept 2"],
      "practice_task": "Practical exercise",
      "estimated_minutes": 60
    }
  ],
  "recommended_books": [
    {
      "title": "Real book title",
      "author": "Author name",
      "why_read": "Why this book is useful for this learner"
    }
  ],
  "youtube_topics": [
    {
      "title": "Learning topic",
      "search_query": "Specific YouTube search phrase"
    }
  ],
  "additional_resources": [
    {
      "title": "Resource name",
      "description": "How the resource helps",
      "search_query": "Useful search phrase"
    }
  ],
  "tips": [
    "Practical learning tip"
  ]
}

Requirements:

1. Include a logical sequence of learning topics, from fundamentals
   to more advanced concepts where appropriate.
2. Include approximately 5 to 12 topics, based on the requested subject,
   level, learning goal, and available time.
3. estimated_minutes must be a positive integer for each topic.
4. Recommend EXACTLY 5 real, relevant books. Provide accurate book
   titles and authors. Do not invent books or authors.
5. Recommend EXACTLY 5 useful YouTube learning topics with specific
   search phrases. Prefer official educational channels or reputable
   instructors when appropriate.
6. Include relevant additional learning resources. Consider official
   documentation, Coursera, edX, MIT OpenCourseWare, freeCodeCamp,
   and academic resources when appropriate for the subject.
7. Do not invent specific URLs. The application will construct search links.
8. Adapt recommendations to the student's level and goal.
9. Keep the content educational, actionable, and easy to understand.
10. Do not calculate the daily schedule. Python will allocate the
    available minutes and generate the final schedule.
11. Return JSON only. Do not use Markdown fences.
"""

    user_payload = {
        "subjects": subjects,
        "total_minutes": total_minutes,
        "days": days,
        "start_date": start_date.isoformat(),
        "break_minutes": break_minutes,
        "goal": goal,
        "level": level,
    }

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": json.dumps(
                    user_payload,
                    ensure_ascii=False,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("OpenAI returned an empty learning roadmap.")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "OpenAI returned invalid JSON for the learning roadmap."
        ) from exc

    # --------------------------------------------------
    # 3. Validate the generated topics
    # --------------------------------------------------
    raw_topics = data.get("topics", [])

    if not isinstance(raw_topics, list) or not raw_topics:
        raise ValueError(
            "The AI did not generate any learning topics. Please try again."
        )

    topics = []

    for index, item in enumerate(raw_topics, start=1):
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()

        if not title:
            continue

        objective = str(item.get("objective", "")).strip()

        concepts = item.get("concepts", [])

        if not isinstance(concepts, list):
            concepts = []

        concepts = [
            str(concept).strip()
            for concept in concepts
            if str(concept).strip()
        ]

        practice_task = str(
            item.get("practice_task", "Review the topic and solve exercises.")
        ).strip()

        try:
            estimated_minutes = max(
                1,
                int(item.get("estimated_minutes", 60)),
            )
        except (TypeError, ValueError):
            estimated_minutes = 60

        topics.append({
            "topic_number": index,
            "title": title,
            "objective": objective,
            "concepts": concepts,
            "practice_task": practice_task,
            "estimated_minutes": estimated_minutes,
        })

    if not topics:
        raise ValueError("No valid learning topics were generated.")

    # --------------------------------------------------
    # 4. Allocate the total study time across topics
    # --------------------------------------------------
    total_estimated = sum(
        topic["estimated_minutes"] for topic in topics
    )

    # Scale AI topic estimates to the student's actual available time.
    allocated_minutes = []
    remaining_minutes = total_minutes

    for index, topic in enumerate(topics):
        if index == len(topics) - 1:
            minutes = remaining_minutes
        else:
            minutes = round(
                total_minutes
                * topic["estimated_minutes"]
                / total_estimated
            )

            # Keep at least one minute for each remaining topic.
            remaining_topics = len(topics) - index - 1
            maximum_minutes = remaining_minutes - remaining_topics
            minutes = max(1, min(minutes, maximum_minutes))

        allocated_minutes.append(minutes)
        remaining_minutes -= minutes

    for topic, minutes in zip(topics, allocated_minutes):
        topic["allocated_minutes"] = minutes

    # --------------------------------------------------
    # 5. Create the daily schedule using Python
    # --------------------------------------------------
    daily_minutes = [total_minutes // days] * days

    for index in range(total_minutes % days):
        daily_minutes[index] += 1

    schedule = []
    topic_index = 0
    topic_minutes_remaining = topics[0]["allocated_minutes"]

    for day_index, day_total in enumerate(daily_minutes):
        current_date = start_date + timedelta(days=day_index)
        tasks = []
        minutes_left_today = day_total

        while minutes_left_today > 0:
            topic = topics[topic_index]

            session_minutes = min(
                minutes_left_today,
                topic_minutes_remaining,
            )

            concepts_text = ", ".join(topic["concepts"])

            activity_parts = []

            if topic["objective"]:
                activity_parts.append(
                    f"Objective: {topic['objective']}"
                )

            if concepts_text:
                activity_parts.append(
                    f"Concepts: {concepts_text}"
                )

            activity_parts.append(
                f"Practice: {topic['practice_task']}"
            )

            activity = " | ".join(activity_parts)

            tasks.append({
                "subject": topic["title"],
                "duration_minutes": session_minutes,
                "activity": activity,
            })

            minutes_left_today -= session_minutes
            topic_minutes_remaining -= session_minutes

            if topic_minutes_remaining == 0:
                topic_index += 1

                if topic_index < len(topics):
                    topic_minutes_remaining = (
                        topics[topic_index]["allocated_minutes"]
                    )
                else:
                    break

        schedule.append({
            "day": day_index + 1,
            "date": current_date.isoformat(),
            "total_minutes": day_total,
            "tasks": tasks,
            "note": (
                f"Take a {break_minutes}-minute break between "
                "study blocks when practical."
            ),
        })

    # --------------------------------------------------
    # 6. Prepare five book recommendations and search links
    # --------------------------------------------------
    books = []

    for item in data.get("recommended_books", [])[:5]:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        author = str(item.get("author", "")).strip()

        if not title or not author:
            continue

        books.append({
            "title": title,
            "author": author,
            "why_read": str(item.get("why_read", "")).strip(),
            "url": (
                "https://books.google.com/books?q="
                + quote_plus(f"{title} {author}")
            ),
        })

    # --------------------------------------------------
    # 7. Prepare five YouTube learning search links
    # --------------------------------------------------
    youtube_resources = []

    for item in data.get("youtube_topics", [])[:5]:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        query = str(item.get("search_query", title)).strip()

        if not title or not query:
            continue

        youtube_resources.append({
            "title": title,
            "url": (
                "https://www.youtube.com/results?search_query="
                + quote_plus(query)
            ),
        })

    # --------------------------------------------------
    # 8. Prepare additional general learning resources
    # --------------------------------------------------
    additional_resources = []

    for item in data.get("additional_resources", []):
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        query = str(item.get("search_query", title)).strip()

        if not title or not query:
            continue

        additional_resources.append({
            "title": title,
            "description": str(
                item.get("description", "")
            ).strip(),
            "url": (
                "https://www.google.com/search?q="
                + quote_plus(query)
            ),
        })

    # Add useful general learning platforms.
    subject_query = " ".join(subjects)

    additional_resources.extend([
        {
            "title": "Coursera",
            "description": (
                "Find structured courses and guided learning paths."
            ),
            "url": (
                "https://www.coursera.org/search?query="
                + quote_plus(subject_query)
            ),
        },
        {
            "title": "edX",
            "description": (
                "Explore university-level courses and learning materials."
            ),
            "url": (
                "https://www.edx.org/search?q="
                + quote_plus(subject_query)
            ),
        },
        {
            "title": "MIT OpenCourseWare",
            "description": (
                "Search for university lectures, notes, and course materials."
            ),
            "url": (
                "https://www.google.com/search?q="
                + quote_plus(
                    "site:ocw.mit.edu " + subject_query
                )
            ),
        },
        {
            "title": "Google Scholar",
            "description": (
                "Search academic papers and research publications."
            ),
            "url": (
                "https://scholar.google.com/scholar?q="
                + quote_plus(subject_query)
            ),
        },
        {
            "title": "Official Documentation",
            "description": (
                "Find official documentation and reference guides "
                "for the requested subject."
            ),
            "url": (
                "https://www.google.com/search?q="
                + quote_plus(subject_query + " official documentation")
            ),
        },
    ])

    # --------------------------------------------------
    # 9. Return the complete result for Streamlit
    # --------------------------------------------------
    tips = data.get("tips", [])

    if not isinstance(tips, list):
        tips = []

    tips = [
        str(tip).strip()
        for tip in tips
        if str(tip).strip()
    ]

    return {
        "summary": str(
            data.get(
                "summary",
                f"Personalized roadmap for {', '.join(subjects)}.",
            )
        ),
        "subjects": subjects,
        "total_minutes": total_minutes,
        "days": days,
        "goal": goal,
        "level": level,
        "topics": topics,
        "schedule": schedule,
        "tips": tips,
        "resources": {
            "books": books,
            "youtube": youtube_resources,
            "additional_links": additional_resources,
        },
        "ai_explanation": (
            "OpenAI generated the learning topics and resource "
            "recommendations. Python validated the topics, allocated "
            "the study time, and built the daily schedule."
        ),
    }
