import { verifyEmail } from "mr-email-checker";


async function readStdin() {
    let input = "";

    for await (const chunk of process.stdin) {
        input += chunk;
    }

    return input;
}


function writeJson(value) {
    process.stdout.write(JSON.stringify(value));
}


function validatePayload(payload) {
    if (
        typeof payload !== "object"
        || payload === null
        || Array.isArray(payload)
    ) {
        throw new Error("Input must be a JSON object.");
    }

    if (
        typeof payload.email !== "string"
        || !payload.email.trim()
    ) {
        throw new Error("email is required.");
    }
}


async function main() {
    const rawInput = await readStdin();

    if (!rawInput.trim()) {
        throw new Error("No JSON input received.");
    }

    let payload;

    try {
        payload = JSON.parse(rawInput);
    } catch {
        throw new Error("Input must be valid JSON.");
    }

    validatePayload(payload);

    const email = payload.email.trim();

    const report = await verifyEmail(email, {
        smtp: {
            enabled: payload.smtp_enabled ?? true,
            from: payload.smtp_from ?? "verify@webartsy.nl",
            heloHost: payload.smtp_helo_host ?? "webartsy.nl",
            timeoutMs: payload.smtp_timeout_ms ?? 10000,
            detectCatchAll: payload.detect_catch_all ?? true,
        },
    });

    writeJson(report);
}


main().catch((error) => {
    const message =
        error instanceof Error
            ? error.stack ?? error.message
            : String(error);

    process.stderr.write(`${message}\n`);
    process.exitCode = 1;
});