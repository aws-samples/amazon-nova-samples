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

// Helper function to add days to a date
const addDays = (date: Date, days: number): string => {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result.toISOString().split('T')[0];
};

// Generate dynamic dates based on today
const today = new Date();
const checkIn1 = addDays(today, 30); // 30 days from now - Free cancellation available
const checkOut1 = addDays(today, 33); // 33 days from now (3-night stay)
const checkIn2 = addDays(today, 5); // 5 days from now - Free cancellation passed, only partial refund
const checkOut2 = addDays(today, 10); // 10 days from now (5-night stay)
const checkIn3 = addDays(today, 15); // 15 days from now - No free cancellation, only partial refund
const checkOut3 = addDays(today, 19); // 19 days from now (4-night stay)
const createdAt1 = addDays(today, -15); // Created 15 days ago
const createdAt2 = addDays(today, -30); // Created 30 days ago
const createdAt3 = addDays(today, -25); // Created 25 days ago

// Mock database
const mockReservations: Reservation[] = [
    {
        reservationId: "RES-12345",
        name: "Angela Park",
        checkInDate: checkIn1,
        checkOutDate: checkOut1,
        hotelName: "Seaview Hotel",
        roomType: "Deluxe Ocean View",
        totalCost: 750.00,
        isPaid: true,
        createdAt: createdAt1,
    },
    {
        reservationId: "RES-23456",
        name: "Don Smith",
        checkInDate: checkIn2,
        checkOutDate: checkOut2,
        hotelName: "Mountain Lodge",
        roomType: "Standard King",
        totalCost: 850.00,
        isPaid: true,
        createdAt: createdAt2,
    },
    {
        reservationId: "RES-34567",
        name: "Maria Rodriguez",
        checkInDate: checkIn3,
        checkOutDate: checkOut3,
        hotelName: "City Central Hotel",
        roomType: "Executive Suite",
        totalCost: 1200.00,
        isPaid: true,
        createdAt: createdAt3,
    }
];

// Generate dynamic cancellation policy dates
const freeCancellation1 = addDays(today, 23); // 7 days before check-in (30 - 7) - Still available
const partialRefund1 = addDays(today, 28); // 2 days before check-in (30 - 2)
const freeCancellation2 = addDays(today, -2); // 7 days before check-in (5 - 7) - Already passed
const partialRefund2 = addDays(today, 3); // 2 days before check-in (5 - 2) - Still available
const partialRefund3 = addDays(today, 8); // 7 days before check-in (15 - 7) - No free cancellation

const mockCancellationPolicies: { [key: string]: CancellationPolicy } = {
    "RES-12345": {
        reservationId: "RES-12345",
        freeCancellationUntil: freeCancellation1, // 7 days before check-in - AVAILABLE: Full refund
        partialRefundUntil: partialRefund1, // 2 days before check-in
        partialRefundPercentage: 50,
        noRefundAfter: partialRefund1,
        additionalNotes: "Free cancellation available",
    },
    "RES-23456": {
        reservationId: "RES-23456",
        freeCancellationUntil: freeCancellation2, // 7 days before check-in - PASSED: Only partial refund
        partialRefundUntil: partialRefund2, // 2 days before check-in - Still available
        partialRefundPercentage: 50,
        noRefundAfter: partialRefund2,
        additionalNotes: "Free cancellation deadline has passed",
    },
    "RES-34567": {
        reservationId: "RES-34567",
        freeCancellationUntil: null, // NO free cancellation - Only partial refund available
        partialRefundUntil: partialRefund3, // 7 days before check-in
        partialRefundPercentage: 50,
        noRefundAfter: partialRefund3,
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
