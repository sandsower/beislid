import { execFile } from "node:child_process";

export interface ExecResult {
	stdout: string;
	stderr: string;
	exitCode: number | null;
	timedOut: boolean;
}

export async function commandExists(command: string): Promise<string | undefined> {
	const probe = process.platform === "win32" ? `where ${command}` : `command -v ${command}`;
	return new Promise((resolve) => {
		execFile(process.platform === "win32" ? "cmd" : "sh", process.platform === "win32" ? ["/c", probe] : ["-c", probe], { timeout: 1500 }, (error, stdout) => {
			resolve(error ? undefined : stdout.trim().split(/\r?\n/)[0]);
		});
	});
}

export async function execFileResult(
	command: string,
	args: string[],
	options: { cwd?: string; timeoutMs?: number; maxBuffer?: number } = {},
): Promise<ExecResult> {
	return new Promise((resolve) => {
		execFile(
			command,
			args,
			{
				cwd: options.cwd,
				timeout: options.timeoutMs,
				maxBuffer: options.maxBuffer ?? 10 * 1024 * 1024,
			},
			(error, stdout, stderr) => {
				const exitCode = typeof error?.code === "number" ? error.code : error ? null : 0;
				resolve({
					stdout: String(stdout ?? ""),
					stderr: String(stderr ?? ""),
					exitCode,
					timedOut: Boolean(error && options.timeoutMs && (error as NodeJS.ErrnoException & { killed?: boolean }).killed),
				});
			},
		);
	});
}

export function psQuote(value: string): string {
	return `'${value.replace(/'/g, "''")}'`;
}

export async function resolvePowerShell(): Promise<string | undefined> {
	return (await commandExists("powershell")) ?? (await commandExists("pwsh"));
}
