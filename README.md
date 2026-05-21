# speakmdfile

言简意赅：念出我的 Markdown 文件

花了二十分钟现学现卖的，能不能用不确定，反正 works on my machine

部分代码请教了 Claude Opus 4.7 老师，但全文都经过了 human review，不过开发者不保证自己能力，介意者勿用

## 如何使用？

0. 将本脚本下到本地，并且安装 Python 3.9 或更高版本

1. 安装依赖

   ```bash
   pip install openai
   ```

2. 准备一个 Markdown 文件 `input.md`：

   ```markdown
   <!-- 第一段 -->

   Hello, this is the first paragraph.

   ---

   <!-- 第二段，用不同音色 -->

   @voice: nova
   This is the second paragraph, read with a different voice.
   ```

3. 运行：

   ```bash
   python main.py \
   -i input.md \
   -u https://api.openai.com/v1 \
   -k sk-xxxxxxxx \
   -m gpt-4o-mini-tts
   ```

4. 到自动创建的 `out_<时间戳>` 目录下找到 `tts_1.mp3` 和 `tts_2.mp3`，收取成果

## 具体语法？

先举个例子：

```markdown
<!-- 下面是三段不同风格的文本 -->

<!-- 第一段：新闻播报 -->

@instructions: Read in the style of a professional news anchor. Calm and authoritative.
China has cemented its position as the world's second-largest economy...

---

<!-- 第二段：教学讲解 -->

@voice: sage
@speed: 0.95
@instructions: Read like a thoughtful educator. Clear and patient.
Artificial intelligence has become a hot topic in recent years...

---

<!-- 第三段：个人书信，用高品质模型 -->

@voice: nova
@model: tts-1-hd
@format: flac
@prefix: letter
Dormitory life is an indispensable part of college life...
```

这个 Markdown 文件将输出三个文件：`tts_1.mp3`、`tts_2.mp3`、`letter_3.flac`

### 段首元数据

在每一段开头，可以用 `@key: value` 的形式覆盖该段的部分朗读参数

元数据必须紧贴段落开头，且元数据之间不能有空行

支持的字段：

- `@voice` —— 该段使用的音色
- `@speed` —— 该段使用的语速
- `@instructions` —— 该段使用的风格提示词
- `@format` —— 该段输出的音频文件格式
- `@model` —— 该段使用的模型
- `@prefix` —— 该段输出文件名的前缀

示例：

```markdown
@voice: sage
@speed: 0.95
@instructions: Read like a thoughtful educator. Clear and patient.
This is the body of the segment...
```

没有写的字段，会自动使用命令行传入的值，或采用默认值

### 分段

用一行 `---`（仅这三个字符，不加任何内容）作为段落分隔符，每一段会生成一个音频文件

```markdown
<!-- 第一段内容 -->

第一行内容
第二行内容

<!-- 每一段内容都可以有很多行 -->

---

<!-- 第二段内容 -->

第一行内容
第二行内容
```

### 注释

支持标准 HTML 注释 `<!-- ... -->`，可以单行也可以跨多行

注释会在处理前被完全剥除，不会发送给 API，最终生成的音频也完全不会包含注释内容

```markdown
<!-- 这是一个说明，不会被念出来 -->

<!--
  你也可以写多行注释，
  比如解释这段为什么用这个音色
-->

@voice: nova
The actual content to be read.
```

## 你可能想知道的小知识

### 输出目录与文件命名

- 没有显式传 `-o` 时，会在当前工作目录下自动创建 `out_<时间戳>/` 作为本次运行的输出根目录，时间戳格式为 `YYYYMMDD_HHMMSS`
- 单文件时，音频文件直接放在输出根目录下
- 多文件时（用多个 `-i` 传入），每个文件的音频会放在以该文件名（去扩展名）命名的子目录下
- 每个音频文件命名格式为 `<prefix>_<段内序号>.<format>`，段内序号会根据该文件的总段数自动补零

> 例如：单个文件 100 段会生成 `tts_001.mp3` 到 `tts_100.mp3`

### 多文件输入

`-i` 可以重复指定，一次处理多个 Markdown 文件：

```bash
python main.py \
-i news.md -i essay.md -i letter.md \
-u https://api.openai.com/v1 \
-k sk-xxxxxxxx \
-m gpt-4o-mini-tts
```

此时输出结构会变成：

```
out_<时间戳>/
├── news/
│   ├── tts_1.mp3
│   └── tts_2.mp3
├── essay/
│   ├── tts_1.mp3
│   └── tts_2.mp3
└── letter/
    └── tts_1.mp3
```

每个文件的段落编号独立从 1 开始，子目录名为对应 Markdown 文件的文件名（去扩展名）

> 单文件时不会创建子目录，音频直接放在 `out_<时间戳>/` 根目录下

### 命令行参数

| 参数             | 简写 | 必填 | 默认值           | 说明                                                      |
| ---------------- | ---- | ---- | ---------------- | --------------------------------------------------------- |
| `--input`        | `-i` | 是   | —                | Markdown 文件路径（可重复指定，传入多个文件）             |
| `--api-url`      | `-u` | 是   | —                | OpenAI 兼容 API 的 Base URL                               |
| `--api-key`      | `-k` | 是   | —                | API 密钥                                                  |
| `--model`        | `-m` | 是   | —                | TTS 模型名（如 `tts-1`、`tts-1-hd`、`gpt-4o-mini-tts`）   |
| `--output-dir`   | `-o` | 否   | `./out_<时间戳>` | 输出目录，不存在会自动创建                                |
| `--voice`        | —    | 否   | `alloy`          | 要让模型使用的 TTS 音色                                   |
| `--format`       | —    | 否   | `mp3`            | 输出格式：`mp3` / `opus` / `aac` / `flac` / `wav` / `pcm` |
| `--speed`        | —    | 否   | `1.0`            | 语速，范围为：`0.25` ~ `4.0`                              |
| `--instructions` | —    | 否   | 空               | 风格提示词（仅部分模型支持）                              |
| `--prefix`       | —    | 否   | `tts`            | 输出文件名前缀                                            |
| `--workers`      | `-w` | 否   | `4`              | 并发请求数（跨文件共享同一个线程池）                      |

### 退出码

- `0` —— 全部成功
- `1` —— 参数或输入错误
- `2` —— 部分段落生成失败

## 许可证

The Unlicense
