interface Reservation {
    reservationId: string;
    name: string;
    checkInDate: string;
    checkOutDate: string;
    hotelName: string;
    roomType: string;
    totalCost: number;
    isPaid: boolean;
    createdAt: string;
}

interface CancellationPolicy {
    reservationId: string;
    freeCancellationUntil: string | null;
    partialRefundUntil: string | null;
    partialRefundPercentage: number;
    noRefundAfter: string;
    additionalNotes: string | null;
}

interface GetReservationParams {
    name: string;
    checkInDate: string;
}

interface CancelReservationParams {
    reservationId: string;
    confirmCancellation: boolean;
}

interface CancellationResult {
    success: boolean;
    reservationId: string;
    cancellationDate: string;
    refundAmount: number;
    refundPercentage: number;
    confirmationCode: string;
    message: string;
}

// Mock database
const mockReservations: Reservation[] = [
    {
        reservationId: "RES-12345",
        name: "Angela Park",
        checkInDate: "2026-04-12",
        checkOutDate: "2026-04-15",
        hotelName: "Seaview Hotel",
        roomType: "Deluxe Ocean View",
        totalCost: 750.00,
        isPaid: true,
        createdAt: "2024-12-15",
    },
    {
        reservationId: "RES-23456",
        name: "Don Smith",
        checkInDate: "2026-05-15",
        checkOutDate: "2026-05-20",
        hotelName: "Mountain Lodge",
        roomType: "Standard King",
        totalCost: 850.00,
        isPaid: true,
        createdAt: "2024-11-30",
    },
    {
        reservationId: "RES-34567",
        name: "Maria Rodriguez",
        checkInDate: "2026-06-10",
        checkOutDate: "2026-06-14",
        hotelName: "City Central Hotel",
        roomType: "Executive Suite",
        totalCost: 1200.00,
        isPaid: true,
        createdAt: "2024-12-05",
    }
];

const mockCancellationPolicies: { [key: string]: CancellationPolicy } = {
    "RES-12345": {
        reservationId: "RES-12345",
        freeCancellationUntil: "2026-04-05", // 7 days before check-in
        partialRefundUntil: "2026-04-10", // 2 days before check-in
        partialRefundPercentage: 50,
        noRefundAfter: "2026-04-10",
        additionalNotes: null,
    },
    "RES-23456": {
        reservationId: "RES-23456",
        freeCancellationUntil: "2026-05-10", // 5 days before check-in
        partialRefundUntil: "2026-05-14", // 1 day before check-in
        partialRefundPercentage: 30,
        noRefundAfter: "2026-05-14",
        additionalNotes: "Non-refundable deposit of $100 applies to all cancellations",
    },
    "RES-34567": {
        reservationId: "RES-34567",
        freeCancellationUntil: null, // No free cancellation
        partialRefundUntil: "2026-06-03", // 7 days before check-in
        partialRefundPercentage: 25,
        noRefundAfter: "2026-06-03",
        additionalNotes: "Special event rate with limited cancellation options",
    }
};

// Helper to get today's date in YYYY-MM-DD format
const getTodayDate = (): string => {
    return new Date().toISOString().split('T')[0];
};

// Tool implementation functions
export const getReservation = async (params: GetReservationParams): Promise<Reservation | null> => {
    console.log(`Looking up reservation for ${params.name} with check-in date ${params.checkInDate}`);

    // Find matching reservation
    const reservation = mockReservations.find(r =>
        r.name.toLowerCase() === params.name.toLowerCase() &&
        r.checkInDate === params.checkInDate
    );

    // If no reservation found, return null
    if (!reservation) {
        return null;
    }

    // Make sure reservation.id exists before using it as an index
    const cancellationPolicy = reservation.reservationId ? mockCancellationPolicies[reservation.reservationId] : null;

    // Add cancellation policy to the reservation
    const reservationWithPolicy = {
        ...reservation,
        cancellationPolicy
    };

    return reservationWithPolicy;
};

export const cancelReservation = async (params: CancelReservationParams): Promise<CancellationResult> => {
    console.log(`Processing cancellation for reservation ${params.reservationId}`);

    // Safety check - must confirm cancellation
    if (!params.confirmCancellation) {
        return {
            success: false,
            reservationId: params.reservationId,
            cancellationDate: getTodayDate(),
            refundAmount: 0,
            refundPercentage: 0,
            confirmationCode: "",
            message: "Cancellation not confirmed by customer"
        };
    }

    // Find the reservation
    const reservation = mockReservations.find(r => r.reservationId === params.reservationId);
    if (!reservation) {
        return {
            success: false,
            reservationId: params.reservationId,
            cancellationDate: getTodayDate(),
            refundAmount: 0,
            refundPercentage: 0,
            confirmationCode: "",
            message: "Reservation not found"
        };
    }

    // Get cancellation policy
    const policy = mockCancellationPolicies[params.reservationId];
    const today = getTodayDate();

    // Calculate refund based on policy
    let refundPercentage = 0;
    let refundAmount = 0;
    let message = "";

    if (policy.freeCancellationUntil && today <= policy.freeCancellationUntil) {
        refundPercentage = 100;
        refundAmount = reservation.totalCost;
        message = "Full refund processed";
    } else if (policy.partialRefundUntil && today <= policy.partialRefundUntil) {
        refundPercentage = policy.partialRefundPercentage;
        refundAmount = reservation.totalCost * (refundPercentage / 100);
        message = `Partial refund of ${refundPercentage}% processed`;
    } else {
        refundPercentage = 0;
        refundAmount = 0;
        message = "No refund is applicable based on cancellation policy";
    }

    // Generate random confirmation code
    const confirmationCode = `CANX-${Math.floor(Math.random() * 1000000).toString().padStart(6, '0')}`;

    return {
        success: true,
        reservationId: params.reservationId,
        cancellationDate: today,
        refundAmount,
        refundPercentage,
        confirmationCode,
        message
    };
};

// Example usage for LLM integration
export const processToolCalls = async (toolName: string, toolInput: any): Promise<any> => {
    switch (toolName) {
        case 'getReservationTool':
            return await getReservation(toolInput);

        case 'cancelReservationTool':
            return await cancelReservation(toolInput);

        default:
            throw new Error(`Unknown tool: ${toolName}`);
    }
};

// Example of handling a tool call from Amazon Nova Sonic
export const handleToolCall = async (toolUse: any): Promise<any> => {
    console.log(`Received tool call: ${JSON.stringify(toolUse)}`);
    const { toolName, content } = toolUse;
    // Parse the content string into a JavaScript object

    const contentObject = JSON.parse(content);
    console.log(`Parsed content: ${JSON.stringify(contentObject)}`);

    try {
        const result = await processToolCalls(toolName, contentObject);
        console.log(`Tool call result: ${JSON.stringify(result)}`);
        if (result != null) {
            return {
                toolResult: {
                    content: [{ result }],
                    status: "success"
                }
            };
        }
        else {
            return {
                toolResult: {
                    content: [{ status: "Reservation not found" }],
                    status: "error"
                }
            };
        }
    } catch (error) {
        const toolResult = {
            toolResult: {
                content: [{ text: `Error processing tool call: ${error}` }],
                status: "error"
            }
        };
        console.log(`Returning tool result: ${JSON.stringify(toolResult)}`);
        return toolResult;
    }
};
