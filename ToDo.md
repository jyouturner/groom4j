# To Do

## Add a Reviwer to Demand Better Results

With same prompt, more advanced model returns much better results, shown below. However, we'd prefer to use less expensive models, therefore, we may want to add a reviewer (grader) to continue to push the LLM

From gpt-3.5-turbo-1106

```
[Step 1]
Identify the file or files where the population field is defined and used. This could be in the domain model, service layer, or controller layer.

[Step 2]
Once the file is identified, locate the specific code segments where the population field is being handled or accessed.

[Step 3]
Update the code to allow the population field to be NULL. This may involve modifying the data type, validation logic, and any related operations that depend on the population field.

[Step 4]
Ensure that the changes are consistent across all layers of the application where the population field is used, including the domain model, service layer, and controller layer.

[Step 5]
Test the updated code to verify that the population field can now be NULL without causing any unexpected behavior or errors.

[Step 6]
If necessary, update any relevant documentation or comments to reflect the changes made to the code.

[Step 7]
Commit the changes to the version control system and communicate the updates to the relevant team members.

[Step 8]
Ensure that the changes are deployed to the appropriate environments and monitor the application for any issues related to the updated code.
```

From gpt-4-1106-preview

```
To update the code to allow the population to be NULL, we need to consider where the population data is being handled in the application. Based on the project structure, it is likely that the population field is part of the `City` domain model and potentially used in DTOs, services, and repositories related to city data. Here are the steps to accomplish the task:

[Step 1]
Update the `City` domain model to allow the population field to be nullable. This involves changing the population field in the `City.java` file within the `com.iky.travel.domain.model` package. If the field is a primitive type (e.g., `int`), change it to the corresponding wrapper class (e.g., `Integer`) which can hold null values.

[Step 2]
Ensure that the `CityDTO` class in the `com.iky.travel.domain.dto` package also reflects this change. If there is a population field in the `CityDTO`, it should also use the wrapper class (e.g., `Integer`) to allow null values.

[Step 3]
Update the `CityMapper` class in the `com.iky.travel.domain.mapper` package to correctly map the nullable population field between the `City` domain model and the `CityDTO`.

[Step 4]
Check the `CityRepository` interface in the `com.iky.travel.domain.repository.city` package to ensure that there are no queries or methods that assume the population field is non-null. If there are any, update the queries to handle null values appropriately.

[Step 5]
Review the `CityService` interface and its implementation in `CityServiceImpl` within the `com.iky.travel.domain.service.city` and `com.iky.travel.domain.service.city.impl` packages, respectively. Ensure that the business logic accounts for the population field being nullable and update any methods that need to handle null values.

[Step 6]
Check the `CityController` class in the `com.iky.travel.controller.city` package to ensure that any incoming requests that include population data are correctly handled when the population is null. Update validation, if necessary, to allow for null values.

[Step 7]
If there are any custom exceptions in the `com.iky.travel.exception.city` package that are thrown in relation to the population field being null, update or remove these exceptions as they may no longer be applicable.

[Step 8]
Review any unit tests that may be affected by this change to ensure they still
```

### Challenges

Based on testing for examle letting GPT-4 to review the steps geneated from GPT-3.5, GPT-4 does not respond with "need improve", even though it can make BETTER results.

So I asked ChatGPT-4 on the evaluation of recordings of Grooming (since it is very very good at this type of things). Here are from ChatGPT-4:


Evaluating the effectiveness of a grooming session using only the text artifact (e.g., notes or records) involves 
analyzing the content for specific characteristics that reflect high-quality grooming practices. Here are some metrics and aspects you can use to assess the text:

* Completeness of Descriptions: Check if tasks, user stories, and acceptance criteria are described with sufficient detail. There should be enough information for anyone reading the document to understand what needs to be done, why it's important, and how to determine when it's completed.

* Clarity and Understandability: Evaluate the language used for clarity and simplicity. Technical jargon should be explained or minimized to ensure that the document is understandable by all stakeholders, including non-technical ones.

* Consistency in Formatting and Structure: Look for a consistent structure and format across the document. This includes the way tasks are numbered or categorized, how estimates are recorded, and the format used for user stories and acceptance criteria.

* Estimation Details: Assess how estimations are provided. Good grooming artifacts include estimations for tasks (e.g., in story points, hours, or days) and an explanation of the rationale behind these estimates, if possible.

* Prioritization Indicators: Determine if the document clearly indicates the priority of tasks and stories. High, medium, and low priorities should be distinguishable, with reasoning for prioritization when necessary.

* Identification of Dependencies and Risks: Look for notes on dependencies between tasks and identified risks. High-quality grooming documents will mention potential blockers or challenges and might also suggest mitigation strategies.

* Definition of Done (DoD): Ensure that the document includes or references a clear Definition of Done for tasks or stories. This might be a checklist or a set of criteria that specifies when a task is considered complete.

* Action Items and Assignees: Check if the document lists action items coming out of the grooming session, along with the team members responsible for them. This shows planning and accountability.

* Feedback and Adjustments: Look for evidence of feedback incorporation from previous sprints or stakeholders. This could be in the form of adjustments to tasks, changes in prioritization, or notes on new requirements.

* Stakeholder Engagement: While harder to quantify, notes that indicate active participation or input from various stakeholders (e.g., product owner, developers, QA engineers) suggest a collaborative grooming process.

To systematically evaluate the grooming session artifact, you could create a checklist or scorecard based on these metrics. Each section of your document could be scored based on how well it meets these criteria, helping identify areas of strength and opportunities for improvement in future grooming sessions.
