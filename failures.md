# SHL Assessment Recommender - Failure Report

This document records the failures identified during the testing of the `/chat` endpoint on `https://shl-assessment-recommender-zh5s.onrender.com/chat`, specifically evaluated against the provided `GenAI_SampleConversations` traces and the `SHL_AI_Intern_Assignment.md` criteria.

## Behavioral and Flow Failures

### 1. Premature Recommendations & Lack of Clarification
*   **Criterion:** "Clarify vague queries before recommending."
*   **Observed Failure:** The sample traces (e.g., C2, C10) demonstrate that the agent should wait and ask clarifying questions (returning `recommendations: []`) in the early turns when context is insufficient. Instead, the deployed app aggressively returns exactly 10 recommendations on **Turn 1** for many traces (C4, C5, C6, C7, C8). It fails to hold back and clarify vague requirements.

### 2. False Triggering of "Comparison" Logic
*   **Criterion:** "Compare when asked."
*   **Observed Failure:** The agent misinterprets general conversation as comparison requests based on naive keyword matching. In **Trace C1**, the user states: *"Selection — comparing candidates against a leadership benchmark."* The endpoint mistakenly triggers its catalog-comparison logic on the word "comparing" and asks: *"Which SHL catalog assessments should I compare? Please provide two assessment names..."* instead of interpreting it as contextual information for a role.

### 3. Mismanagement of `end_of_conversation` Flag
*   **Criterion:** `end_of_conversation` is `true` only when the agent considers the task complete.
*   **Observed Failure:** Because the agent aggressively outputs 10 recommendations on Turn 1, it also prematurely sets `end_of_conversation: true` on Turn 1. The sample traces show that the conversation should remain open (`false`) during the refinement phase, only closing when the user signals they are satisfied with the final shortlist. The deployed logic breaks this multi-turn design by effectively ending the conversation immediately.

### 4. Precision vs. Padding in Shortlists
*   **Criterion:** Recommend between 1 and 10 assessments once it has enough context.
*   **Observed Failure:** The sample traces indicate highly scoped, precise shortlists (e.g., exactly 3 items in C1, exactly 5 items in C2). The deployed application consistently "pads" its response to exactly 10 items almost every time. When it exhausts highly relevant tests, it includes generic or tangentially related assessments to reach the count of 10, significantly reducing the precision (Recall@K accuracy) of the shortlist.

### 5. Out-of-Scope (General Hiring Advice)
*   **Criterion:** Refuse general hiring advice.
*   **Observed Failure:** When asked "How many stages should my interview process have?", instead of a firm refusal, the agent attempts to accommodate the request by responding: *"To determine the ideal number of stages for your interview process, consider the role, seniority, and assessment focus."* This violates the strict out-of-scope rules.

### 6. Refinement Appending Constraints
*   **Criterion:** Refine when the user changes constraints mid-conversation.
*   **Observed Failure:** When tasked to append new constraints to an already established shortlist (e.g., "Actually, add personality tests too" after a list of Java tests is returned), the agent updates its conversational text acknowledging the addition but fails to actually update the JSON `recommendations` array. It returns the exact same list of 10 technical tests without appending the requested personality test.

### 7. Drill-Down Refinement (Partial Pass / Flow Failure)
*   **Criterion:** "Refine when the user changes constraints mid-conversation."
*   **Observed Partial Pass:** When asked to filter an existing list of recommendations (e.g., *"Only show me the entry-level ones from that list"*), the agent successfully understands the new constraint context ("entry-level").
*   **Observed Failure:** Instead of seamlessly filtering the existing array and returning the updated shortlist, the agent drops back into its clarification loop, replying: *"For an entry-level Java developer, I can show you entry-level assessments. What focus would you like..."* with 0 recommendations, disrupting the flow.

### 8. Hybrid Intents & Intent Collision
*   **Criterion:** Handle realistic, multi-faceted user inputs.
*   **Observed Failure:** When a query contains both a request for recommendation and a comparison (e.g., *"I need a test for a Java developer. Also, what is the difference between 'Java 8' and 'Core Java'?"*), the agent fails to address both intents. It completely ignores the primary recommendation request and gets stuck in a loop trying to resolve ambiguities in the comparison logic.

### 9. Handling Ambiguity ("No Preference")
*   **Criterion:** "The simulated user... says it has no preference when asked something outside its facts" (From Evaluation methodology).
*   **Observed Failure:** When the agent asks for a seniority level and the user replies *"I have no preference"*, the agent fails to accept this as a valid non-constraint. Instead of providing a broad list of recommendations, it loops and essentially re-asks the same question: *"For a Java developer, consider seniority level and assessment focus to choose a suitable evaluation method."* 

### 10. Anaphoric Reference (Pronoun Resolution / Conversational Memory)
*   **Criterion:** "Translate the catalog, the user's goal, and the conversation history into prompts..."
*   **Observed Partial Pass:** After requesting tests for a Python developer, the user follows up with: *"Do you have any tests for their manager?"* The agent correctly resolves that "their" refers to the Python developer and understands the request is for a managerial role.
*   **Observed Failure:** Despite understanding the intent, the agent fails to execute the retrieval. It replies with a generic statement: *"We have tests for managerial roles"* and returns 0 recommendations, completely halting the conversational momentum instead of returning the requested shortlist.
