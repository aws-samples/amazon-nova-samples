## Amazon Nova Models

Welcome to the Amazon Nova Model Getting Started!

###  Nova 2.0 models overview

###  Nova 1.0 models overview

Here is the markdown table based on the information provided in the image:

| Model Characteristics      | Amazon Nova Premier                          | Amazon Nova Pro                                 | Amazon Nova Lite                             | Amazon Nova Micro                                          |
| -------------------------- | -------------------------------------------- | ----------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| Model ID                   | us.amazon.nova-premier-v1:0                  | us.amazon.nova-pro-v1:0                         | us.amazon.nova-lite-v1:0                     | us.amazon.nova-micro-v1:0                                  |
| Input modalities           | Text, Image, Video                           | Text, Image, Video                              | Text, Image, Video                           | Text                                                       |
| Output Modalities          | Text                                         | Text                                            | Text                                         | Text                                                       |
| Context Window             | 1M                                           | 300k                                            | 300k                                         | 130k                                                       |
| Max Output Tokens\*        | 10K                                          | 5k                                              | 5k                                           | 5k                                                         |
| Supported Languages        | 200+\*\*                                     | 200+\*\*                                        | 200+\*\*                                     | EN; DE; ES; FR; JA; AR; HI; IT; PT; NL; ZH; KO; TR; HE; RU |
| Regions                    | us-east-1, us-west-2, us-west-1              | us-east-1                                       | us-east-1                                    | us-east-1                                                  |
| Document Support           | pdf, csv, doc, docx, xls, xlsx, html, txt md | pdf, csv, doc, docx, xls, xlsx, html, txt md    | pdf, csv, doc, docx, xls, xlsx, html, txt md | Text                                                       |
| Converse API               | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| InvokeAPI                  | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Streaming                  | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Batch Inference            | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Fine Tuning                | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Provisioned Throughput     | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Bedrock Knowledge Bases    | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Bedrock Agents             | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Bedrock Guardrails         | Yes(text only)                               | Yes(text only)                                  | Yes(text only)                               | Yes                                                        |
| Bedrock Evaluations        | Yes(text only)                               | Yes(text only)                                  | Yes(text only)                               | Yes                                                        |
| Bedrock Prompt flows       | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Bedrock Studio             | Yes                                          | Yes                                             | Yes                                          | Yes                                                        |
| Bedrock Model Distillation | Teacher to: Pro, Lite, and Micro             | Teacher to: Lite and Micro; Student of: Premier | Student of: Premier and Pro                  | Student of: Premier and Pro                                |

- Degradation may occur past 200k token (equivalent to approximately 150K words, or 65 documents, or 20min of video)
  \*\* Optimized for German, Spanish, French, Italian, Japanese, Korean, Arabic, Simplified Chinese, Russian, Hindi, Portuguese, Dutch, Turkish, and Hebrew
