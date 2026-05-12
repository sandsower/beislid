import type { NeedsCaptureBlock, NeedsCaptureStatus } from "./schema.js";
import { addBlock } from "./store.js";

export interface AddNeedsCaptureInput {
	deckId: string;
	sectionId: string;
	title?: string;
	reason: string;
	request?: string;
	status?: NeedsCaptureStatus;
}

export async function addNeedsCaptureBlock(input: AddNeedsCaptureInput): Promise<{ deckId: string; sectionId: string; blockId: string }> {
	const block: Omit<NeedsCaptureBlock, "id"> = {
		type: "needs-capture",
		title: input.title,
		reason: input.reason,
		request: input.request,
		status: input.status ?? "NEEDS CAPTURE",
	};
	const result = await addBlock(input.deckId, input.sectionId, block);
	return { deckId: result.doc.id, sectionId: input.sectionId, blockId: result.blockId };
}
