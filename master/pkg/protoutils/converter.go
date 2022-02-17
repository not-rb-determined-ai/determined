package protoutils

import (
	"time"

	"github.com/pkg/errors"
	"google.golang.org/protobuf/types/known/structpb"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// ProtoConverter just holds errors, allowing you to convert a large number of fields on a protobuf
// struct without checking errors until afterwards.
type ProtoConverter struct {
	err error
}

// Error returns the error collected during the conversions, if any.
func (c *ProtoConverter) Error() error {
	return c.err
}

// ToStruct converts a model.JSONObj-like type into a structpb.Struct type, remembering the error
// if any is encountered.
func (c *ProtoConverter) ToStruct(x map[string]interface{}, what string) *structpb.Struct {
	if c.err != nil {
		return nil
	}
	out, err := structpb.NewStruct(x)
	if err != nil {
		c.err = errors.Wrapf(err, "error converting %v to protobuf", what)
	}
	return out
}

// ToTimestamp converts a time.Time into a timestamppb.Timestamp.
func (c *ProtoConverter) ToTimestamp(x time.Time) *timestamppb.Timestamp {
	return timestamppb.New(x)
}
