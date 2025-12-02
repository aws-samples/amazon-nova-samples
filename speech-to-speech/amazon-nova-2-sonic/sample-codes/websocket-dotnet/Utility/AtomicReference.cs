using System.Threading;

namespace NovaSonicWebSocket.Utility
{
    public class AtomicReference<T> where T : class
    {
        private T _value;
        
        public AtomicReference(T initialValue)
        {
            _value = initialValue;
        }
        
        public T Value
        {
            get { return Interlocked.CompareExchange(ref _value, null!, null!); }
            set { Interlocked.Exchange(ref _value, value); }
        }
        
        public T GetAndSet(T newValue)
        {
            return Interlocked.Exchange(ref _value, newValue);
        }
        
        public bool CompareAndSet(T expected, T newValue)
        {
            return Interlocked.CompareExchange(ref _value, newValue, expected) == expected;
        }
        
        public override string ToString()
        {
            T value = Value;
            return value?.ToString() ?? "null";
        }
    }
}
