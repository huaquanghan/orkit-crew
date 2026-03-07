"""Code Generator Agent - Phase 3 of the PRD-to-Product pipeline.

This agent takes the approved plan and generates actual Next.js project files on disk.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from crewai import Agent, Task

from orkit_crew.agents.base import BaseAgent
from orkit_crew.core.prd_parser import PRDDocument
from orkit_crew.core.session import PipelinePhase, SessionManager


class CodeGeneratorAgent(BaseAgent):
    """Agent for generating Next.js code based on implementation plan.

    Takes the approved plan and generates actual Next.js project files on disk,
    following best practices for TypeScript, Tailwind CSS, and shadcn/ui.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        llm_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Code Generator agent.

        Args:
            session_manager: Optional session manager for state tracking.
            llm_config: Optional LLM configuration for CrewAI.
        """
        super().__init__(session_manager, llm_config)
        self.generated_files: list[str] = []
        self.tasks: list[dict[str, Any]] = []

    @property
    def role(self) -> str:
        """Agent role."""
        return "Senior Next.js Developer"

    @property
    def goal(self) -> str:
        """Agent goal."""
        return (
            "Generate production-quality Next.js code based on implementation plan. "
            "Create clean, maintainable code following TypeScript best practices, "
            "Tailwind CSS conventions, and Next.js App Router patterns. "
            "Use Server Components by default and 'use client' only when needed."
        )

    @property
    def backstory(self) -> str:
        """Agent backstory."""
        return (
            "You are a senior frontend developer with deep expertise in Next.js App Router, "
            "React Server Components, TypeScript, Tailwind CSS, and shadcn/ui. "
            "You write clean, type-safe code with proper error handling. "
            "You follow modern React patterns, use Server Components by default, "
            "and only add 'use client' when interactivity is required. "
            "Your code is well-organized, properly formatted, and production-ready."
        )

    async def generate(
        self,
        prd_doc: PRDDocument,
        analysis: str,
        plan: str,
        output_dir: str,
    ) -> list[str]:
        """Generate Next.js project from PRD, analysis, and plan.

        Args:
            prd_doc: Parsed PRD document.
            analysis: Approved analysis content.
            plan: Approved plan content.
            output_dir: Output directory path.

        Returns:
            List of generated file paths.
        """
        # Update session phase
        if self.session_manager:
            self.session_manager.start_phase(PipelinePhase.GENERATING)

        # Parse tasks from plan
        self.tasks = self._parse_tasks_from_plan(plan)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self.generated_files = []

        # Generate each task
        for task in self.tasks:
            task_files = await self.generate_task(task, prd_doc, analysis, plan, output_path)
            self.generated_files.extend(task_files)

            # Track in session
            if self.session_manager:
                for f in task_files:
                    self.session_manager.track_file(f, task.get("title", "unknown"))

        # Complete phase
        if self.session_manager:
            self.session_manager.complete_phase(PipelinePhase.GENERATING)

        return self.generated_files

    async def generate_task(
        self,
        task: dict[str, Any],
        prd_doc: PRDDocument,
        analysis: str,
        plan: str,
        output_dir: Path,
    ) -> list[str]:
        """Generate code for a single task.

        Args:
            task: Task dictionary with file info.
            prd_doc: Parsed PRD document.
            analysis: Analysis content.
            plan: Full plan content.
            output_dir: Output directory path.

        Returns:
            List of generated file paths.
        """
        task_type = task.get("type", "").lower()
        files = task.get("files", [])
        description = task.get("description", "")
        title = task.get("title", "")

        generated: list[str] = []

        # Handle setup task specially
        if task_type == "setup":
            generated = await self._generate_setup_files(prd_doc, output_dir)
        elif files:
            # Generate each file in the task
            for file_path in files:
                content = await self._generate_file_content(
                    file_path=file_path,
                    task=task,
                    prd_doc=prd_doc,
                    analysis=analysis,
                    plan=plan,
                )
                full_path = self.write_file(output_dir, file_path, content)
                generated.append(full_path)
        else:
            # No specific files, generate based on description
            content = await self._generate_from_description(
                description=description,
                title=title,
                prd_doc=prd_doc,
                analysis=analysis,
                plan=plan,
            )
            # Infer file path from task
            file_path = self._infer_file_path(task, prd_doc)
            full_path = self.write_file(output_dir, file_path, content)
            generated.append(full_path)

        return generated

    async def _generate_setup_files(
        self,
        prd_doc: PRDDocument,
        output_dir: Path,
    ) -> list[str]:
        """Generate Next.js setup files (package.json, configs, etc.).

        Args:
            prd_doc: Parsed PRD document.
            output_dir: Output directory path.

        Returns:
            List of generated file paths.
        """
        generated: list[str] = []
        metadata = prd_doc.metadata
        stack = metadata.stack

        # package.json
        package_json = self._generate_package_json(metadata)
        generated.append(self.write_file(output_dir, "package.json", package_json))

        # tsconfig.json
        tsconfig = self._generate_tsconfig()
        generated.append(self.write_file(output_dir, "tsconfig.json", tsconfig))

        # tailwind.config.ts
        tailwind_config = self._generate_tailwind_config(metadata)
        generated.append(self.write_file(output_dir, "tailwind.config.ts", tailwind_config))

        # next.config.mjs
        next_config = self._generate_next_config(metadata)
        generated.append(self.write_file(output_dir, "next.config.mjs", next_config))

        # postcss.config.mjs
        postcss_config = self._generate_postcss_config()
        generated.append(self.write_file(output_dir, "postcss.config.mjs", postcss_config))

        # components.json (shadcn/ui)
        components_json = self._generate_components_json(metadata)
        generated.append(self.write_file(output_dir, "components.json", components_json))

        # src/app/layout.tsx
        layout = self._generate_layout(metadata)
        generated.append(self.write_file(output_dir, "src/app/layout.tsx", layout))

        # src/app/page.tsx
        page = self._generate_home_page(prd_doc)
        generated.append(self.write_file(output_dir, "src/app/page.tsx", page))

        # src/app/globals.css
        globals_css = self._generate_globals_css()
        generated.append(self.write_file(output_dir, "src/app/globals.css", globals_css))

        # src/lib/utils.ts
        utils_ts = self._generate_utils_ts()
        generated.append(self.write_file(output_dir, "src/lib/utils.ts", utils_ts))

        # Create directories
        (output_dir / "src" / "components" / "ui").mkdir(parents=True, exist_ok=True)
        (output_dir / "public").mkdir(parents=True, exist_ok=True)

        return generated

    def _generate_package_json(self, metadata: Any) -> str:
        """Generate package.json content."""
        project_name = metadata.project_name.lower().replace(" ", "-")
        stack = metadata.stack

        dependencies = {
            "next": "^15.0.0",
            "react": "^19.0.0",
            "react-dom": "^19.0.0",
        }

        dev_dependencies = {
            "typescript": "^5.0.0",
            "@types/node": "^20.0.0",
            "@types/react": "^19.0.0",
            "@types/react-dom": "^19.0.0",
        }

        # Add stack-specific dependencies
        if stack.styling == "tailwind":
            dev_dependencies["tailwindcss"] = "^3.4.0"
            dev_dependencies["postcss"] = "^8.4.0"
            dev_dependencies["autoprefixer"] = "^10.4.0"

        if stack.ui_library == "shadcn":
            dependencies["class-variance-authority"] = "^0.7.0"
            dependencies["clsx"] = "^2.1.0"
            dependencies["tailwind-merge"] = "^2.2.0"
            dependencies["@radix-ui/react-slot"] = "^1.0.2"

        package_data = {
            "name": project_name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
                "type-check": "tsc --noEmit",
            },
            "dependencies": dependencies,
            "devDependencies": dev_dependencies,
        }

        return json.dumps(package_data, indent=2)

    def _generate_tsconfig(self) -> str:
        """Generate tsconfig.json content."""
        return json.dumps({
            "compilerOptions": {
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        }, indent=2)

    def _generate_tailwind_config(self, metadata: Any) -> str:
        """Generate tailwind.config.ts content."""
        return '''import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
'''

    def _generate_next_config(self, metadata: Any) -> str:
        """Generate next.config.mjs content."""
        return '''/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
};

export default nextConfig;
'''

    def _generate_postcss_config(self) -> str:
        """Generate postcss.config.mjs content."""
        return '''/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
'''

    def _generate_components_json(self, metadata: Any) -> str:
        """Generate components.json (shadcn/ui) content."""
        return json.dumps({
            "$schema": "https://ui.shadcn.com/schema.json",
            "style": "default",
            "rsc": True,
            "tsx": True,
            "tailwind": {
                "config": "tailwind.config.ts",
                "css": "src/app/globals.css",
                "baseColor": "slate",
                "cssVariables": True,
                "prefix": "",
            },
            "aliases": {
                "components": "@/components",
                "utils": "@/lib/utils",
            },
        }, indent=2)

    def _generate_layout(self, metadata: Any) -> str:
        """Generate src/app/layout.tsx content."""
        project_name = metadata.project_name

        return f'''import type {{ Metadata }} from "next";
import {{ Inter }} from "next/font/google";
import "./globals.css";

const inter = Inter({{ subsets: ["latin"] }});

export const metadata: Metadata = {{
  title: "{project_name}",
  description: "Generated by Orkit Crew",
}};

export default function RootLayout({{
  children,
}}: Readonly<{{
  children: React.ReactNode;
}}>) {{
  return (
    <html lang="en">
      <body className={{inter.className}}>{{children}}</body>
    </html>
  );
}}
'''

    def _generate_home_page(self, prd_doc: PRDDocument) -> str:
        """Generate src/app/page.tsx content."""
        project_name = prd_doc.metadata.project_name
        features = prd_doc.content.features[:3]  # Show first 3 features

        features_list = ""
        for f in features:
            features_list += f"          <li>✓ {{f.name}}</li>\n"

        return f'''export default function HomePage() {{
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          Welcome to {project_name}
        </h1>
        
        <p className="text-center text-lg mb-8 text-muted-foreground">
          Your Next.js app is ready!
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
          <div className="p-6 border rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Features</h2>
            <ul className="space-y-2 text-muted-foreground">
{features_list}            </ul>
          </div>
          
          <div className="p-6 border rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Get Started</h2>
            <ol className="space-y-2 text-muted-foreground list-decimal list-inside">
              <li>Run <code>npm install</code></li>
              <li>Run <code>npm run dev</code></li>
              <li>Open <code>http://localhost:3000</code></li>
            </ol>
          </div>
        </div>
      </div>
    </main>
  );
}}
'''

    def _generate_globals_css(self) -> str:
        """Generate src/app/globals.css content."""
        return '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
'''

    def _generate_utils_ts(self) -> str:
        """Generate src/lib/utils.ts content."""
        return '''import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
'''

    async def _generate_file_content(
        self,
        file_path: str,
        task: dict[str, Any],
        prd_doc: PRDDocument,
        analysis: str,
        plan: str,
    ) -> str:
        """Generate content for a specific file using LLM.

        Args:
            file_path: Relative file path.
            task: Task dictionary.
            prd_doc: PRD document.
            analysis: Analysis content.
            plan: Plan content.

        Returns:
            Generated file content.
        """
        prompt = self._build_file_generation_prompt(
            file_path=file_path,
            task=task,
            prd_doc=prd_doc,
            analysis=analysis,
            plan=plan,
        )

        agent = self.get_agent()
        generation_task = Task(
            description=prompt,
            agent=agent,
            expected_output=f"Complete, production-ready code for {file_path}",
        )

        result = generation_task.execute_sync()
        content = str(result)

        # Extract code from markdown if present
        content = self._extract_code_from_markdown(content, file_path)

        return content

    def _build_file_generation_prompt(
        self,
        file_path: str,
        task: dict[str, Any],
        prd_doc: PRDDocument,
        analysis: str,
        plan: str,
    ) -> str:
        """Build prompt for file generation.

        Args:
            file_path: Relative file path.
            task: Task dictionary.
            prd_doc: PRD document.
            analysis: Analysis content.
            plan: Plan content.

        Returns:
            Generation prompt.
        """
        metadata = prd_doc.metadata
        stack = metadata.stack

        file_type = self._get_file_type(file_path)

        prompt = f"""Generate complete, production-ready code for the following file.

## File Information

**File Path:** `{file_path}`
**File Type:** {file_type}
**Task:** {task.get("title", "")}
**Description:** {task.get("description", "")}

## Technology Stack

- Framework: {stack.framework}
- Language: {stack.language}
- Styling: {stack.styling}
- UI Library: {stack.ui_library}
- Router: {metadata.nextjs.router}

## Project Context

**Project:** {metadata.project_name}

**Features to implement:**
"""
        for feature in prd_doc.content.features[:5]:
            prompt += f"\n- {feature.name} ({feature.priority.value}): {feature.description[:100]}"

        prompt += f"""

## Analysis Summary

{analysis[:800]}...

## Implementation Plan

{plan[:600]}...

## Code Requirements

1. Use TypeScript with proper types (no `any`)
2. Use Tailwind CSS classes for styling
3. Follow Next.js App Router conventions
4. Use Server Components by default
5. Only add 'use client' when interactivity is required
6. Import shadcn/ui components from @/components/ui
7. Use the cn() utility from @/lib/utils for class merging
8. Include proper error handling
9. Add JSDoc comments for functions and components
10. Export components as default where appropriate

## Output

Provide ONLY the complete code for `{file_path}`. Do not include markdown code block markers (```) or explanations. The code should be ready to save directly to the file.
"""
        return prompt

    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from path."""
        if file_path.endswith(".tsx"):
            if "page.tsx" in file_path:
                return "Next.js Page Component"
            elif "layout.tsx" in file_path:
                return "Next.js Layout Component"
            elif "loading.tsx" in file_path:
                return "Next.js Loading UI"
            elif "error.tsx" in file_path:
                return "Next.js Error UI"
            elif "/components/" in file_path:
                return "React Component"
            else:
                return "TypeScript React"
        elif file_path.endswith(".ts"):
            if "/lib/" in file_path or "/utils/" in file_path:
                return "Utility Module"
            elif "/types/" in file_path:
                return "Type Definitions"
            elif "/hooks/" in file_path:
                return "Custom Hook"
            else:
                return "TypeScript Module"
        elif file_path.endswith(".css"):
            return "CSS Stylesheet"
        elif file_path.endswith(".json"):
            return "JSON Configuration"
        else:
            return "Unknown"

    def _extract_code_from_markdown(self, content: str, file_path: str) -> str:
        """Extract code from markdown code blocks.

        Args:
            content: Content that may contain markdown.
            file_path: File path for context.

        Returns:
            Clean code content.
        """
        # Look for code blocks
        code_block_pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(code_block_pattern, content, re.DOTALL)

        if matches:
            # Return the first code block content
            return matches[0].strip()

        # No code blocks found, return as-is
        return content.strip()

    async def _generate_from_description(
        self,
        description: str,
        title: str,
        prd_doc: PRDDocument,
        analysis: str,
        plan: str,
    ) -> str:
        """Generate code from description when no specific files given.

        Args:
            description: Task description.
            title: Task title.
            prd_doc: PRD document.
            analysis: Analysis content.
            plan: Plan content.

        Returns:
            Generated code.
        """
        prompt = f"""Generate code based on the following task description.

## Task

**Title:** {title}
**Description:** {description}

## Context

**Project:** {prd_doc.metadata.project_name}
**Stack:** {prd_doc.metadata.stack.framework}, {prd_doc.metadata.stack.language}

Generate appropriate TypeScript/React code for this task. Use proper types, Tailwind classes, and follow Next.js conventions.
"""

        agent = self.get_agent()
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="Complete TypeScript/React code",
        )

        result = task.execute_sync()
        return self._extract_code_from_markdown(str(result), "")

    def _infer_file_path(self, task: dict[str, Any], prd_doc: PRDDocument) -> str:
        """Infer file path from task when not specified.

        Args:
            task: Task dictionary.
            prd_doc: PRD document.

        Returns:
            Inferred file path.
        """
        task_type = task.get("type", "").lower()
        title = task.get("title", "").lower()

        # Map task types to directories
        if task_type == "component":
            return f"src/components/{self._to_pascal_case(title)}.tsx"
        elif task_type == "page":
            # Extract route from title or use slug
            route = self._to_kebab_case(title.replace("page", "").strip())
            return f"src/app/{route}/page.tsx"
        elif task_type == "api":
            route = self._to_kebab_case(title.replace("api", "").strip())
            return f"src/app/api/{route}/route.ts"
        elif task_type == "config":
            return f"config/{self._to_kebab_case(title)}.ts"
        else:
            return f"src/lib/{self._to_kebab_case(title)}.ts"

    def _to_pascal_case(self, text: str) -> str:
        """Convert text to PascalCase."""
        words = re.findall(r"[a-zA-Z0-9]+", text)
        return "".join(w.capitalize() for w in words)

    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case."""
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return "-".join(words)

    def write_file(
        self,
        output_dir: Path,
        relative_path: str,
        content: str,
    ) -> str:
        """Write content to file.

        Args:
            output_dir: Base output directory.
            relative_path: Relative file path.
            content: File content.

        Returns:
            Absolute file path.
        """
        file_path = output_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return str(file_path.absolute())

    async def revise_file(
        self,
        file_path: str,
        feedback: str,
        context: dict[str, Any],
    ) -> str:
        """Revise a single file based on feedback.

        Args:
            file_path: Path to file to revise.
            feedback: User feedback.
            context: Context including PRD, analysis, plan.

        Returns:
            Revised file content.
        """
        # Read current content
        path = Path(file_path)
        current_content = path.read_text(encoding="utf-8")

        prompt = f"""Revise the following file based on user feedback.

## File Path

`{file_path}`

## Current Content

```typescript
{current_content}
```

## User Feedback

{feedback}

## Context

**Project:** {context.get("prd_doc", {}).metadata.project_name if context.get("prd_doc") else "Unknown"}

## Your Task

Provide the revised code that addresses the feedback. Maintain the same file structure and conventions. Return ONLY the code, no markdown markers.
"""

        agent = self.get_agent()
        task = Task(
            description=prompt,
            agent=agent,
            expected_output="Revised file content",
        )

        result = task.execute_sync()
        revised = self._extract_code_from_markdown(str(result), file_path)

        # Write revised content
        path.write_text(revised, encoding="utf-8")

        return revised

    def _parse_tasks_from_plan(self, plan_content: str) -> list[dict[str, Any]]:
        """Extract tasks from plan content.

        Args:
            plan_content: Plan markdown content.

        Returns:
            List of task dictionaries.
        """
        tasks: list[dict[str, Any]] = []

        # Pattern to match task headers
        task_pattern = r"\*\*Task\s+(\d+):\s*([^\*]+)\*\*"

        for match in re.finditer(task_pattern, plan_content):
            task_num = int(match.group(1))
            task_title = match.group(2).strip()

            # Find task section
            start_pos = match.end()
            next_task = re.search(r"\*\*Task\s+\d+:", plan_content[start_pos:])
            if next_task:
                end_pos = start_pos + next_task.start()
                task_section = plan_content[start_pos:end_pos]
            else:
                task_section = plan_content[start_pos:]

            task = self._parse_task_section(task_num, task_title, task_section)
            tasks.append(task)

        return tasks

    def _parse_task_section(
        self,
        task_num: int,
        task_title: str,
        task_section: str,
    ) -> dict[str, Any]:
        """Parse individual task section.

        Args:
            task_num: Task number.
            task_title: Task title.
            task_section: Task section content.

        Returns:
            Task dictionary.
        """
        task: dict[str, Any] = {
            "number": task_num,
            "title": task_title,
            "type": "",
            "files": [],
            "description": "",
            "dependencies": [],
            "complexity": "medium",
            "criteria": [],
        }

        # Extract type
        type_match = re.search(r"[\*\-]\s*\*?Type:?\*?\*?:?\s*(\w+)", task_section)
        if type_match:
            task["type"] = type_match.group(1).lower()

        # Extract files
        files_match = re.search(r"[\*\-]\s*\*?Files:?\*?\*?:?\s*(.+?)(?=\n|$)", task_section)
        if files_match:
            files_text = files_match.group(1)
            task["files"] = re.findall(r"`([^`]+)`", files_text)

        # Extract description
        desc_match = re.search(
            r"[\*\-]\s*\*?Description:?\*?\*?:?\s*(.+?)(?=\n[\*\-]|\Z)",
            task_section,
            re.DOTALL,
        )
        if desc_match:
            task["description"] = desc_match.group(1).strip()

        # Extract dependencies
        deps_match = re.search(r"[\*\-]\s*\*?Dependencies:?\*?\*?:?\s*(.+?)(?=\n|$)", task_section)
        if deps_match:
            deps_text = deps_match.group(1)
            task["dependencies"] = [int(n) for n in re.findall(r"Task\s+(\d+)", deps_text)]

        # Extract complexity
        complexity_match = re.search(r"[\*\-]\s*\*?Complexity:?\*?\*?:?\s*(\w+)", task_section)
        if complexity_match:
            task["complexity"] = complexity_match.group(1).lower()

        return task

    async def execute(self, *args: Any, **kwargs: Any) -> str:
        """Execute agent's main task.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Summary of generated files.
        """
        prd_doc = kwargs.get("prd_doc")
        analysis = kwargs.get("analysis", "")
        plan = kwargs.get("plan", "")
        output_dir = kwargs.get("output_dir", "./output")

        if prd_doc is None:
            raise ValueError("prd_doc is required")

        files = await self.generate(prd_doc, analysis, plan, output_dir)
        return f"Generated {len(files)} files:\n" + "\n".join(f"  - {f}" for f in files)
