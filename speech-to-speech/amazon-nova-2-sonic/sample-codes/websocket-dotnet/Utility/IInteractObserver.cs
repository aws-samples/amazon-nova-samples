namespace NovaSonicWebSocket.Utility;

/// <summary>
/// Interface for the observer pattern used in the interaction flow
/// </summary>
/// <typeparam name="T">The type of message being observed</typeparam>
public interface IInteractObserver<T>
{
    void OnNext(T msg);
    
    void OnComplete();
    
    // TODO: Create a new class for Error Status
    void OnError(Exception error);
}
