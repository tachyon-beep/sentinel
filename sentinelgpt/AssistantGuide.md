# OpenAI Assistants API Guide

The Assistants API allows you to build AI assistants within your own applications. An Assistant has instructions and can leverage models, tools, and files to respond to user queries. The Assistants API currently supports three types of tools: Code Interpreter, File Search, and Function calling.

## Key Features

- **Model Integration:** Assistants can call OpenAI's models with specific instructions to tune their personality and capabilities.
- **Tool Access:** Assistants can access multiple tools in parallel, including OpenAI-hosted tools like `code_interpreter` and `file_search`, or custom tools via function calling.
- **Persistent Threads:** Threads store message history and truncate when the conversation exceeds the model's context length. This simplifies AI application development by maintaining context.
- **File Handling:** Assistants can access files in various formats. They can create files and reference them in messages. Tools can also create files, e.g., images or spreadsheets.

## Objects

- **Assistant:** A purpose-built AI that uses OpenAI's models and calls tools.
- **Thread:** A conversation session between an Assistant and a user. Threads store messages and automatically handle truncation to fit the model's context.
- **Message:** A message created by an Assistant or a user. Messages can include text, images, and other files. Stored as a list on the Thread.
- **Run:** An invocation of an Assistant on a Thread. The Assistant uses its configuration and the Thread's messages to perform tasks by calling models and tools. During a Run, the Assistant appends messages to the Thread.
- **Run Step:** A detailed list of steps the Assistant took during a Run. These steps can include tool calls or message creation.

## Typical Integration Flow

1. **Create an Assistant** by defining its custom instructions and picking a model. If helpful, add files and enable tools like Code Interpreter, File Search, and Function calling.
2. **Create a Thread** when a user starts a conversation.
3. **Add Messages to the Thread** as the user asks questions.
4. **Run the Assistant on the Thread** to generate a response by calling the model and the tools.

## Creating Assistants

To get started, create an Assistant by specifying the model and optionally customizing its behavior:

- **Instructions:** Guide the Assistant's personality and goals (similar to system messages in the Chat Completions API).
- **Tools:** Provide access to up to 128 tools, including OpenAI-hosted tools and third-party tools via function calling.
- **Tool Resources:** Grant tools like `code_interpreter` and `file_search` access to files. Files must be uploaded with the purpose set to `assistants`.

### Example: Creating a Math Tutor Assistant

```python
assistant = client.beta.assistants.create(
  name="Math Tutor",
  instructions="You are a personal math tutor. Write and run code to answer math questions.",
  tools=[{"type": "code_interpreter"}],
  model="gpt-4o",
)
```

## Managing Threads and Messages

Threads and Messages represent a conversation session between an Assistant and a user.

### Creating a Thread with Messages

```python
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "I need to solve the equation `3x + 11 = 14`. Can you help me?"
    }
  ]
)
```

## Creating a Run

Once all the user Messages have been added to the Thread, you can Run the Thread with any Assistant. Creating a Run uses the model and tools associated with the Assistant to generate a response. These responses are added to the Thread as assistant Messages.

### Example: Creating and Streaming a Run

```python
with client.beta.threads.runs.stream(
  thread_id=thread.id,
  assistant_id=assistant.id,
  event_handler=EventHandler(),
) as stream:
  stream.until_done()
```

## File Search (Beta)

File Search augments the Assistant with knowledge from outside its model, such as proprietary product information or documents provided by your users. OpenAI automatically parses and chunks your documents, creates and stores the embeddings, and uses both vector and keyword search to retrieve relevant content to answer user queries.

### How It Works

The `file_search` tool implements several retrieval best practices to help you extract the right data from your files and augment the model's responses. The `file_search` tool:

- Rewrites user queries to optimize them for search.
- Breaks down complex user queries into multiple searches it can run in parallel.
- Runs both keyword and semantic searches across both assistant and thread vector stores.
- Reranks search results to pick the most relevant ones before generating the final response.

### Vector Stores

Vector Store objects give the File Search tool the ability to search your files. Adding a file to a vector_store automatically parses, chunks, embeds, and stores the file in a vector database capable of both keyword and semantic search. Each vector_store can hold up to 10,000 files. Vector stores can be attached to both Assistants and Threads.

### Attaching Vector Stores

You can attach vector stores to your Assistant or Thread using the `tool_resources` parameter.

```python
assistant = client.beta.assistants.create(
  instructions="You are a helpful product support assistant and you answer questions based on the files provided to you.",
  model="gpt-4o",
  tools=[{"type": "file_search"}],
  tool_resources={
    "file_search": {
      "vector_store_ids": ["vs_1"]
    }
  }
)
```

## Best Practices and Limitations

- Implement authorization and restrict API key access.
- Create separate accounts for different applications.
- Ensure all files in a vector_store are fully processed before creating a run.
- Customize `file_search` tool settings like chunking configuration and number of chunks returned.
- Manage costs with expiration policies on vector_store objects.

The Assistants API has a few known limitations:

- Lack of support for deterministic pre-search filtering using custom metadata.
- No support for parsing images within documents (including images of charts, graphs, tables, etc.)
- Limited support for retrievals over structured file formats (like csv or jsonl).
- Summarization capabilities are not yet optimized.

With the Assistants API, you can build powerful AI assistants that leverage OpenAI's models, access multiple tools, maintain conversation context, and augment their knowledge with file search capabilities. By following best practices and understanding current limitations, you can create engaging and effective AI experiences within your applications.

## Error Codes

This guide includes an overview of error codes you might see from both the API and our official Python library. Each error code mentioned in the overview has a dedicated section with further guidance.

### API Errors

| CODE | OVERVIEW |
|------|----------|
| 401 - Invalid Authentication | **Cause:** Invalid Authentication **Solution:** Ensure the correct API key and requesting organization are being used. |
| 401 - Incorrect API key provided | **Cause:** The requesting API key is not correct. **Solution:** Ensure the API key used is correct, clear your browser cache, or generate a new one. |
| 401 - You must be a member of an organization to use the API | **Cause:** Your account is not part of an organization. **Solution:** Contact us to get added to a new organization or ask your organization manager to invite you to an organization. |
| 403 - Country, region, or territory not supported | **Cause:** You are accessing the API from an unsupported country, region, or territory. **Solution:** Please see this page for more information. |
| 429 - Rate limit reached for requests | **Cause:** You are sending requests too quickly. **Solution:** Pace your requests. Read the Rate limit guide. |
| 429 - You exceeded your current quota, please check your plan and billing details | **Cause:** You have run out of credits or hit your maximum monthly spend. **Solution:** Buy more credits or learn how to increase your limits. |
| 500 - The server had an error while processing your request | **Cause:** Issue on our servers. **Solution:** Retry your request after a brief wait and contact us if the issue persists. Check the status page. |
| 503 - The engine is currently overloaded, please try again later | **Cause:** Our servers are experiencing high traffic. **Solution:** Please retry your requests after a brief wait. |

#### Common API Error Codes

- 401 - Invalid Authentication
- 401 - Incorrect API key provided
- 401 - You must be a member of an organization to use the API
- 429 - Rate limit reached for requests
- 429 - You exceeded your current quota, please check your plan and billing details
- 503 - The engine is currently overloaded, please try again later

### Python Library Error Types

| TYPE | OVERVIEW |
|------|----------|
| APIConnectionError | **Cause:** Issue connecting to our services. **Solution:** Check your network settings, proxy configuration, SSL certificates, or firewall rules. |
| APITimeoutError | **Cause:** Request timed out. **Solution:** Retry your request after a brief wait and contact us if the issue persists. |
| AuthenticationError | **Cause:** Your API key or token was invalid, expired, or revoked. **Solution:** Check your API key or token and make sure it is correct and active. You may need to generate a new one from your account dashboard. |
| BadRequestError | **Cause:** Your request was malformed or missing some required parameters, such as a token or an input. **Solution:** The error message should advise you on the specific error made. Check the documentation for the specific API method you are calling and make sure you are sending valid and complete parameters. You may also need to check the encoding, format, or size of your request data. |
| ConflictError | **Cause:** The resource was updated by another request. **Solution:** Try to update the resource again and ensure no other requests are trying to update it. |
| InternalServerError | **Cause:** Issue on our side. **Solution:** Retry your request after a brief wait and contact us if the issue persists. |
| NotFoundError | **Cause:** Requested resource does not exist. **Solution:** Ensure you are using the correct resource identifier. |
| PermissionDeniedError | **Cause:** You don't have access to the requested resource. **Solution:** Ensure you are using the correct API key, organization ID, and resource ID. |
| RateLimitError | **Cause:** You have hit your assigned rate limit. **Solution:** Pace your requests. Read more in our Rate limit guide. |
| UnprocessableEntityError | **Cause:** Unable to process the request despite the format being correct. **Solution:** Please try the request again. |

#### Common Python Library Error Types

- APIConnectionError
- APITimeoutError
- AuthenticationError
- BadRequestError
- InternalServerError
- RateLimitError

### Persistent Errors

If the issue persists, contact our support team via chat and provide them with the following information:

- The model you were using
- The error message and code you received
- The request data and headers you sent
- The timestamp and timezone of your request
- Any other relevant details that may help us diagnose the issue

Our support team will investigate the issue and get back to you as soon as possible. Note that our support queue times may be long due to high demand. You can also post in our Community Forum but be sure to omit any sensitive information.

### Handling Errors

We advise you to programmatically handle errors returned by the API. To do so, you may want to use a code snippet like below:

```python
import openai
from openai import OpenAI

client = OpenAI()

try:
    # Make your OpenAI API request here
    response = client.completions.create(
        prompt="Hello world",
        model="gpt-3.5-turbo-instruct"
    )
except openai.APIError as e:
    # Handle API error here, e.g. retry or log
    print(f"OpenAI API returned an API Error: {e}")
    pass
except openai.APIConnectionError as e:
    # Handle connection error here
    print(f"Failed to connect to OpenAI API: {e}")
    pass
except openai.RateLimitError as e:
    # Handle rate limit error (we recommend using exponential backoff)
    print(f"OpenAI API request exceeded rate limit: {e}")
    pass
